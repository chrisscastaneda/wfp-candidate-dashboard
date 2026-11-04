"""Live Voter Turnout ENR (livevoterturnout.com/ENR/<client>/<n>/en/<token>_Index_<n>.html), used by Orange County.

One large HTML page with every contest. The page name has a random token, so it's found from the county's own
results page, which embeds it. Each contest is a "list-item" block in a "Contest Group" (City, School, Judicial,
United States Representative, ...):

  <span id="raceHeading_<race>" class="sr-only">Contest: <title>, VOTE FOR <n></span>
  <td data-race="<race>" data-contestant="<id>" data-candidate="true"> ... <span ...>NAME</span>
  <td data-race="<race>" data-contestant="<id>" data-votes="true">123</td>

Incumbents are starred ("*LARRY AGRAN"); the star is dropped.
"""
import html
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

# Contest groups that are the county's share of statewide or district races.
SHARE_GROUPS = {"State of California", "United States Representative", "State Senator",
                "Member of the State Assembly"}

_HEADING = re.compile(r'<span id="raceHeading_(\d+)" class="sr-only">Contest: (.*?)</span>', re.S)
_CANDIDATE = re.compile(r'data-race="(\d+)" data-contestant="(\d+)" data-candidate="true"[^>]*>\s*<span[^>]*>(.*?)'
                        r'</span>', re.S)
_VOTES = re.compile(r'data-race="(\d+)" data-contestant="(\d+)" data-votes="true"[^>]*>([\d,]*)</td>')
_GROUP = re.compile(r'<div id="listid_(\d+)" data-group="\d+".*?aria-label="Contest Group ([^"]+)"', re.S)

# Pages without contest groups (San Diego): these offices are the county's share of a statewide or district race,
# which the state's own feed reports in full.
_STATEWIDE = {"governor", "lt_governor", "secretary_of_state", "controller", "treasurer", "attorney_general",
              "insurance_commissioner", "superintendent"}
_DISTRICT = {"federal_senate", "federal_house", "state_senate", "state_house", "board_of_equalization"}
# State propositions are numbered ("PROP 1 - ...", "San Bernardino County PROPOSITION 1"); local measures are lettered.
_STATE_PROP = re.compile(r"(?i)\bprop(osition)?\s+\d+\b")
_PARTY_SUFFIX = re.compile(r"\s*\((DEM|REP|LIB|GRN|PF|AI|NPP)\)\s*$")


def _is_share(title: str, kind: str) -> bool:
    return (kind in _STATEWIDE or kind in _DISTRICT or "PORTION ONLY" in title.upper()
            or bool(re.search(r"(?i)supreme court|court of appeal|^state of california\b", title)))


def _choice(name: str, votes: int, cid: str, is_measure: bool) -> Choice:
    """San Diego appends the party: "XAVIER BECERRA (DEM)"."""
    m = _PARTY_SUFFIX.search(name)
    party = names.party(m.group(1)) if m else None
    name = name[:m.start()] if m else name
    return Choice(names.yes_no(name) if is_measure else name, votes, party, choice_id=cid)


def parse(page: str, *, source_id: str, state: str, jurisdiction: str) -> list[Contest]:
    groups = dict(_GROUP.findall(page))
    votes = {(race, cid): names.to_int(v) for race, cid, v in _VOTES.findall(page)}
    candidates: dict[str, list[tuple[str, str]]] = {}
    for race, cid, name in _CANDIDATE.findall(page):
        candidates.setdefault(race, []).append((cid, html.unescape(name).lstrip("*").strip()))
    contests = []
    for race, heading in _HEADING.findall(page):
        heading = html.unescape(heading).strip()
        m = re.match(r"(.*?),\s*VOTE FOR (\d+)\s*$", heading, re.I)
        title, vote_for = (m.group(1), int(m.group(2))) if m else (heading, 1)
        group = groups.get(race, "")
        rows = candidates.get(race, [])
        is_measure = group.startswith("Measures") or {n.upper() for _, n in rows} <= {"YES", "NO"}
        kind = "measure" if is_measure else names.office_type(title)
        if group in ("City", "School", "Districts", "County") and kind not in ("judicial", "measure"):
            kind = "local"
        if not groups and kind in _STATEWIDE and re.search(r"\b(CITY|COUNTY)\b|-", title, re.I):
            kind = "local"  # "CITY OF CARLSBAD TREASURER", "TREASURER-TAX COLLECTOR"
        share = group in SHARE_GROUPS if groups else _is_share(title, kind)
        contest = Contest(
            source=source_id, contest_id=race, state=state, title=title, office_type=kind,
            district=(names.measure_id(title) or names.fold(title)[:60]) if is_measure else names.district(title),
            # State propositions are listed with local measures; the county's copy is only its share.
            jurisdiction=jurisdiction, vote_for=vote_for,
            scope="partial" if share or _STATE_PROP.search(title) else "complete",
            reporting=Reporting(),
            choices=[_choice(n, votes.get((race, cid), 0), cid, is_measure) for cid, n in rows])
        contest.fill_percentages()
        contests.append(contest)
    return contests


class LiveVoterTurnoutSource(Source):
    platform = "Live Voter Turnout ENR"
    level = "county"

    def __init__(self, id, state, county, landing_url, election_title, tiers=(4,)):
        self.id, self.state, self.county, self.tiers = id, state, county, frozenset(tiers)
        self.title = f"{county} County (Live Voter Turnout)"
        self.site_name, self.url = f"{county} County Registrar of Voters", landing_url
        self.landing_url, self.election_title = landing_url, election_title

    def pull(self, fetch):
        landing = fetch.get(self.landing_url, expect="text")
        if "election-title" in landing:
            # San Diego's results address redirects to the results page itself. It names no election date, so
            # also require a last-updated time on or after election day.
            title = re.search(r'election-title"[^>]*>(.*?)</h1>', landing, re.S)
            stamps = [datetime.strptime(d, "%m/%d/%Y").date()
                      for d in re.findall(r"\b(\d{1,2}/\d{1,2}/\d{4}) \d{1,2}:\d{2}", landing)]
            if (title and self.election_title.lower() in title.group(1).lower()
                    and any(d >= config.ELECTION_DATE for d in stamps)):
                return parse(landing, source_id=self.id, state=self.state, jurisdiction=f"{self.county} County")
            raise NotPublished(f"{self.landing_url} isn't the {self.election_title} of {config.ELECTION_DATE}")
        # The county page can link several elections (Orange: 23 = June primary, 24 = Nov 3); newest first.
        links = sorted(set(re.findall(r'https://www\.livevoterturnout\.com/ENR/[^"\']+_Index_(\d+)\.html', landing)),
                       key=int, reverse=True)
        urls = {n: re.search(rf'https://www\.livevoterturnout\.com/ENR/[^"\']+_Index_{n}\.html', landing).group(0)
                for n in links}
        for n in links:
            page = fetch.get(urls[n], expect="text")
            title = re.search(r'election-title"[^>]*>(.*?)</h1>', page, re.S)
            if title and self.election_title.lower() in title.group(1).lower():
                return parse(page, source_id=self.id, state=self.state, jurisdiction=f"{self.county} County")
        raise NotPublished(f"no linked results page is for the {self.election_title}")
