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


def parse(payload: dict, *, source_id: str, state: str, jurisdiction: str, skip_titles=frozenset()) -> list[Contest]:
    election = payload.get("election") or {}
    contests = []
    for item in payload.get("ballotItems") or []:
        title = _text(item.get("name")).strip()
        if names.fold(title) in skip_titles:
            continue
        is_measure = item.get("contestType") == "BallotMeasure"
        status = item.get("reportingStatus") or {}
        choices = []
        for option in (item.get("summaryResults") or {}).get("ballotOptions") or []:
            label = _text(option.get("name"))
            if option.get("isWriteIn") and not option.get("voteCount"):
                continue
            # RI appends the party to the name ("Amy J. Santiago (DEM)"); Utah's county files prefix it
            # ("DEM DAVID CHAPPELL").
            label = re.sub(r"\s*\((?:DEM|REP|IND|Ind|Soc|LIB|GRN|Lib|Grn|NP|[A-Z][a-z]{2})\)\s*$", "", label)
            label = re.sub(r"^(?:DEM|REP|LIB|CON|UNA|FWD|IAP|GRN|IND)\s+(?=\S)", "", label)
            party = option.get("party")
            choices.append(Choice(
                names.yes_no(label) if is_measure else label, names.to_int(option.get("voteCount")),
                names.party(_text(party.get("name")) if isinstance(party, dict) else party),
                choice_id=option.get("id")))
        contest = Contest(
            source=source_id, contest_id=item["id"], state=state, title=title,
            office_type="measure" if is_measure else names.office_type(title),
            district=names.measure_id(title) or names.fold(title) if is_measure else names.district(title),
            jurisdiction=item.get("parentJurisdictionName") or jurisdiction, vote_for=_vote_for(item),
            final=bool(election.get("isOfficialResults")),
            reporting=Reporting(status.get("reportingUnits"), status.get("totalUnits")),
            feed_updated_at=status.get("asOf") or election.get("lastUpdated"), choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class EnhancedVotingSource(Source):
    platform = "Enhanced Voting"

    def __init__(self, id, state, title, base, jurisdiction, localities=(), tiers=(1, 2, 3, 4)):
        self.id, self.state, self.title = id, state, title
        self.base, self.jurisdiction, self.localities = base.rstrip("/"), jurisdiction, list(localities)
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
        contests = parse(data, source_id=self.id, state=self.state, jurisdiction=_text(info.get("name")))
        seen = frozenset(names.fold(c.title) for c in contests)
        by_name = {names.fold(_text(c.get("name"))): c.get("shortName") for c in info.get("childLocalities") or []}
        for locality in self.localities:
            short = by_name.get(names.fold(locality))
            if not short:
                continue  # not listed (yet, or misspelled here); its races show as unmatched in matches.csv
            local = fetch.get(self._api(f"elections/{short}/{election_id}/data"))
            contests += parse(local, source_id=self.id, state=self.state, jurisdiction=locality, skip_titles=seen)
        return contests
