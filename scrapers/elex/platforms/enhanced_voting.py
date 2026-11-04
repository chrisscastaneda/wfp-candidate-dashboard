"""Enhanced Voting results sites (GA, UT, WA, RI). One JSON per election with every ballot item.

  <base>/results/public/api/jurisdictions/<jurisdiction>                 -> elections[] (publicElectionId, date)
  <base>/results/public/api/elections/<jurisdiction>/<electionId>/data   -> ballotItems[]

Some states put single-county contests only on county sub-sites (Utah's single-county legislative districts are
on salt-lake-county-ut, not the state file). Name those counties in `localities`; their files are read with the
state's election ID, and any contest already in the state file is skipped so multi-county races aren't counted
twice.
"""
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source


def _text(localized) -> str:
    if isinstance(localized, list):
        for item in localized:
            if item.get("languageId") == "en":
                return item.get("text") or ""
        return localized[0].get("text", "") if localized else ""
    return localized or ""


def _vote_for(item) -> int:
    m = re.search(r"\d+", _text(item.get("voteFor")))
    return int(m.group()) if m else 1


def _reporting(status: dict, by_precinct: bool, units: tuple[str, str]) -> Reporting:
    """State files count localities (counties, or RI's cities and towns), and one counts as soon as it posts its
    first batch, so a single-county district reads "100%" on early votes alone. Those get a count instead of a
    percentage. Locality files count precincts, which are fine as a percentage."""
    done, total = status.get("reportingUnits"), status.get("totalUnits")
    if by_precinct and total:
        # Westchester counts a precinct as reporting once any of its ballots are in; the details split that into
        # fully and partly reported, and only fully reported precincts count toward the percentage.
        details = {d.get("reportingStatusClientTextKey"): d.get("value") or 0
                   for d in status.get("reportingStatusDetails") or []}
        if "reporting-status-fully-reported" in details:
            full = details["reporting-status-fully-reported"]
            partly = details.get("reporting-status-partially-reported", 0)
            text = f"{full} of {total} precincts fully reported" + (f", {partly} partly" if partly else "")
            return Reporting(full, total, text=text)
    if by_precinct or not total:
        return Reporting(done, total)
    noun = units[0] if total == 1 else units[1]
    return Reporting(done, total, text=f"{done or 0} of {total} {noun} posted results", as_percent=False)


def parse(payload: dict, *, source_id: str, state: str, jurisdiction: str, skip_titles=frozenset(),
          units=("county", "counties")) -> list[Contest]:
    election = payload.get("election") or {}
    by_precinct = bool(payload.get("precincts"))
    contests = []
    for item in payload.get("ballotItems") or []:
        title = _text(item.get("name")).strip()
        if names.fold(title) in skip_titles:
            continue
        is_measure = item.get("contestType") == "BallotMeasure"
        status = item.get("reportingStatus") or {}
        # New York lists a candidate once per party line (Democratic and Working Families); those combine into one
        # choice, with each line's votes in `party_lines`.
        by_label: dict[str, Choice] = {}
        for option in (item.get("summaryResults") or {}).get("ballotOptions") or []:
            label = _text(option.get("name"))
            if option.get("isWriteIn") and not option.get("voteCount"):
                continue
            # RI appends the party to the name ("Amy J. Santiago (DEM)"); Utah's county files prefix it
            # ("DEM DAVID CHAPPELL"); Monroe, Rockland and Suffolk prefix the fusion line ("WOR Kevin Berry").
            label = re.sub(r"\s*\((?:DEM|REP|IND|Ind|Soc|LIB|GRN|Lib|Grn|NP|[A-Z][a-z]{2})\)\s*$", "", label)
            label = re.sub(r"^(?:DEM|REP|LIB|CON|UNA|FWD|IAP|GRN|IND|WOR|WFP)\s+(?=\S)", "", label)
            party = option.get("party")
            code = names.party(_text(party.get("name")) if isinstance(party, dict) else party)
            votes = names.to_int(option.get("voteCount"))
            label = names.yes_no(label) if is_measure else label
            choice = by_label.get(label)
            if choice is None:
                by_label[label] = Choice(label, votes, code, choice_id=option.get("id"),
                                         party_lines={code: votes} if code else None)
                continue
            choice.votes += votes
            if code:
                choice.party_lines = choice.party_lines or {}
                choice.party_lines[code] = choice.party_lines.get(code, 0) + votes
                if choice.party in (None, "WFP") and code != "WFP":
                    choice.party = code  # show the main line ("DEM"), not WFP's fusion line
        contest = Contest(
            source=source_id, contest_id=item["id"], state=state, title=title,
            office_type="measure" if is_measure else names.office_type(title),
            district=names.measure_id(title) or names.fold(title) if is_measure else names.district(title),
            jurisdiction=item.get("parentJurisdictionName") or jurisdiction, vote_for=_vote_for(item),
            final=bool(election.get("isOfficialResults")),
            reporting=_reporting(status, by_precinct, units),
            feed_updated_at=status.get("asOf") or election.get("lastUpdated"), choices=list(by_label.values()))
        contest.fill_percentages()
        contests.append(contest)
    return contests


def _county_share(contests: list[Contest], county: str) -> None:
    """A county's own file: its state, federal and Supreme Court contests are only the county's share (partial).
    Every contest is labeled with the county, since state contests carry the state's name ("newyork")."""
    for contest in contests:
        contest.jurisdiction = county
        if contest.office_type not in ("local", "measure", "judicial") or "supreme court" in contest.title.lower():
            contest.scope = "partial"


class EnhancedVotingSource(Source):
    platform = "Enhanced Voting"

    def __init__(self, id, state, title, site_name, base, jurisdiction, localities=(), tiers=(1, 2, 3, 4),
                 units=("county", "counties"), level="state", county=None):
        self.id, self.state, self.title, self.site_name, self.units = id, state, title, site_name, units
        self.level, self.county = level, county
        self.base, self.jurisdiction, self.localities = base.rstrip("/"), jurisdiction, list(localities)
        self.url = f"{self.base}/results/public/{jurisdiction}"
        self.tiers = frozenset(tiers)

    def _api(self, path):
        return f"{self.base}/results/public/api/{path}"

    def pull(self, fetch):
        info = fetch.get(self._api(f"jurisdictions/{self.jurisdiction}"))
        wanted = config.ELECTION_DATE.isoformat()
        election = next((e for e in info.get("elections") or [] if (e.get("electionDate") or "")[:10] == wanted), None)
        if not election:
            raise NotPublished(f"no {wanted} election listed for {self.jurisdiction}")
        election_id = election["publicElectionId"]
        data = fetch.get(self._api(f"elections/{self.jurisdiction}/{election_id}/data"))
        contests = parse(data, source_id=self.id, state=self.state, jurisdiction=_text(info.get("name")),
                         units=self.units)
        if self.county:
            _county_share(contests, f"{self.county} County")
        seen = frozenset(names.fold(c.title) for c in contests)
        by_name = {names.fold(_text(c.get("name"))): c.get("shortName") for c in info.get("childLocalities") or []}
        for locality in self.localities:
            short = by_name.get(names.fold(locality))
            if not short:
                continue  # not listed (yet, or misspelled here); its races show as unmatched in matches.csv
            local = fetch.get(self._api(f"elections/{short}/{election_id}/data"))
            contests += parse(local, source_id=self.id, state=self.state, jurisdiction=locality, skip_titles=seen,
                              units=self.units)
        return contests
