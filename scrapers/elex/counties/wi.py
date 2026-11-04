"""Wisconsin county sources. The state doesn't compile election-night results, so these read the counties that post
something scripts can use:

  Dane      public API (api.danecounty.gov/api/v1/elections): list -> election by date; electionresults/<id> -> every
            race with candidate votes and precincts reported
  Kenosha   results page (apps.kenoshacounty.org/ElectionResults_v4/?eid=<n>): one contestBox per race, "1234
            (56.78%)" per candidate and a last-updated time; no precincts-reporting count

Milwaukee County's results page blocks scripts (403), and Racine and Brown post PDFs, so they aren't here.

A county's share of a statewide or multi-county race is partial. Districts that lie entirely inside one county are
listed in `whole_districts` and kept complete: Dane has Assembly District 76 (Madison), Kenosha has Assembly Districts
64 and 65.
"""
import html
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

_PARTY_PREFIX = re.compile(r"^(DEM|REP|LIB|CON|GRN|IND|NON|WGR|DSA)\s+")


def _candidate(label: str) -> tuple[str, str | None]:
    """'DEM Tip McGuire' -> ('Tip McGuire', 'DEM'); running mates ('A /B') keep only the first name."""
    label = re.sub(r"\s+", " ", html.unescape(label)).strip()
    m = _PARTY_PREFIX.match(label)
    party = m.group(1) if m else None
    name = label[m.end():] if m else label
    return name.split(" /")[0].strip(), party


def _scope(kind: str, district: str | None, whole: frozenset) -> str:
    if kind in ("local", "judicial"):
        return "complete"
    return "complete" if (kind, district) in whole else "partial"


def _measure_or_office(title: str) -> tuple[str, str | None]:
    if re.search(r"\b(referendum|question|ref)\b", title, re.I):
        return "measure", names.measure_id(title) or names.fold(title)[:60]
    return names.office_type(title), names.district(title)


def parse_dane(payload: dict, whole: frozenset) -> list[Contest]:
    contests = []
    for race in payload.get("Races") or []:
        title = race["RaceName"].strip()
        if title.upper().startswith(("BALLOTS CAST", "REGISTERED VOTERS")):
            continue
        kind, district = _measure_or_office(title)
        choices = []
        for cand in race.get("Candidates") or []:
            if cand["Name"].lower().startswith("write-in") and not cand.get("Votes"):
                continue
            name, party = _candidate(cand["Name"])
            if kind == "measure":
                name = names.yes_no(name)
            choices.append(Choice(name, names.to_int(cand.get("Votes")), names.party(cand.get("PartyCode")) or party,
                                  choice_id=str(cand.get("Number"))))
        contest = Contest(
            source="wi.dane", contest_id=race["RaceNumber"], state="WI", title=title, office_type=kind,
            district=district, jurisdiction="Dane County", scope=_scope(kind, district, whole),
            reporting=Reporting(race.get("PrecinctsReported"), race.get("TotalPrecincts")),
            feed_updated_at=payload.get("LastPublished"), choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


def parse_kenosha(page: str, whole: frozenset) -> list[Contest]:
    updated = re.search(r"Last updated:(?:&nbsp;|\s)*([\d/]+ [\d:]+ [AP]M)", page)
    updated_at = datetime.strptime(updated.group(1), "%m/%d/%Y %I:%M:%S %p").isoformat() if updated else None
    contests = []
    for i, box in enumerate(page.split('<div class="contestBox">')[1:], start=1):
        title = re.sub(r"<[^>]+>", "", re.search(r"<h1>(.*?)</h1>", box, re.S).group(1)).strip()
        kind, district = _measure_or_office(title)
        vote_for = re.search(r"\(Vote for (\d+)\)", box)
        choices = []
        for label, votes in re.findall(r'class="candtd">(.*?)</td>.*?z-index: 1">([\d,]+) \(', box, re.S):
            name, party = _candidate(re.sub(r"<[^>]+>", "", label))
            if name.lower().startswith("write-in") and not names.to_int(votes):
                continue
            if kind == "measure":
                name = names.yes_no(name)
            choices.append(Choice(name, names.to_int(votes), party, choice_id=name))
        contest = Contest(
            source="wi.kenosha", contest_id=title, state="WI", title=title, office_type=kind, district=district,
            jurisdiction="Kenosha County", scope=_scope(kind, district, whole),
            vote_for=int(vote_for.group(1)) if vote_for else 1, feed_updated_at=updated_at, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Dane(Source):
    id = "wi.dane"
    state = "WI"
    level = "county"
    county = "Dane"
    title = "Dane County Clerk results API"
    site_name = "Dane County Clerk"
    url = "https://elections.countyofdane.com/election-result"
    platform = "Dane County API"
    tiers = frozenset({2, 4})
    whole_districts = frozenset({("state_house", "76")})
    api = "https://api.danecounty.gov/api/v1/elections/"

    def pull(self, fetch):
        wanted = config.ELECTION_DATE.isoformat()
        election = next((e for e in fetch.get(self.api + "list") if (e.get("ElectionDate") or "")[:10] == wanted),
                        None)
        if not election:
            raise NotPublished(f"no {wanted} election listed")
        return parse_dane(fetch.get(self.api + f"electionresults/{election['ElectionId']}"), self.whole_districts)


class Kenosha(Source):
    id = "wi.kenosha"
    state = "WI"
    level = "county"
    county = "Kenosha"
    title = "Kenosha County results page"
    site_name = "Kenosha County Clerk"
    platform = "Kenosha County ElectionResults (HTML)"
    tiers = frozenset({2, 4})
    whole_districts = frozenset({("state_house", "64"), ("state_house", "65")})
    election_id = 70  # the county's id for the Nov 3, 2026 election (?eid=); 69 was the August primary
    url = f"https://apps.kenoshacounty.org/ElectionResults_v4/?eid={election_id}"

    def pull(self, fetch):
        page = fetch.get(self.url, expect="text")
        if f"{config.ELECTION_DATE.month}/{config.ELECTION_DATE.day}/{config.ELECTION_DATE.year}" not in page:
            raise NotPublished(f"election {self.election_id} isn't the {config.ELECTION_DATE} election")
        return parse_kenosha(page, self.whole_districts)


SOURCES = [Dane(), Kenosha()]
