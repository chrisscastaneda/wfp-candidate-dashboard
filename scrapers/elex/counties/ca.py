"""California county sources: Los Angeles's results API and the counties on Clarity ENR.

The state API (states/ca.py) has no local races; these do. County results include the county's share of state and
federal contests, which are marked partial and ignored by the matcher.

Los Angeles (results.lavote.gov), the JSON its results page uses:
  /ElectionResults/GetMenuElections?year=<y>        -> [{ID, Date, Title}]
  /ElectionResults/GetElectionData?electionID=<id>  -> ContestGroups[] -> Contests[] -> Candidates[] (Name, Votes)
"""
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..platforms.clarity import ClaritySource
from ..platforms.livevoterturnout import LiveVoterTurnoutSource
from ..source import NotPublished, Source

LA = "https://results.lavote.gov/ElectionResults/"

# Group names whose contests are statewide or district races the state API already reports in full.
_LA_SHARES = {"Governor", "Lieutenant Governor", "Secretary of State", "Controller", "Treasurer", "Attorney General",
              "Insurance Commissioner", "Board of Equalization", "U.S. Representative", "State Senator",
              "Member of the Assembly", "Supreme Court Justices", "Appellate Court Justices",
              "Superintendent Public Inst", "State Measures"}


def parse_la(data: dict) -> list[Contest]:
    contests = []
    for group in data.get("ContestGroups") or []:
        share = group.get("Name") in _LA_SHARES
        for item in group.get("Contests") or []:
            title = re.sub(r"\s+", " ", item.get("Title") or "").strip()
            is_measure = item.get("Type") == "Measure"
            kind = "measure" if is_measure else names.office_type(title)
            if group.get("Name") in ("Cities", "Schools", "Library Districts", "Water Districts",
                                     "Recreation and Park", "Sheriff") and kind not in ("judicial",):
                kind = "local"  # "CITY OF ... Member of the City Council" isn't a state office
            choices = [Choice(names.yes_no(c["Name"]) if is_measure else c["Name"], names.to_int(c.get("Votes")),
                              names.party(c.get("Party")), choice_id=str(c.get("ID")))
                       for c in item.get("Candidates") or []]
            contest = Contest(
                source="ca.los_angeles", contest_id=str(item["ID"]), state="CA", title=title, office_type=kind,
                district=(names.measure_id(title) or title.split()[-1].lower()) if is_measure
                else names.district(title), jurisdiction="Los Angeles County",
                scope="partial" if share else "complete", vote_for=names.vote_for(item.get("VoteFor")),
                reporting=Reporting(names.to_int(item.get("PrecinctsReporting")) if "PrecinctsReporting" in item
                                    else None, item.get("PrecinctCount") or None), choices=choices)
            contest.fill_percentages()
            contests.append(contest)
    return contests


class LosAngeles(Source):
    id = "ca.los_angeles"
    state = "CA"
    level = "county"
    county = "Los Angeles"
    title = "Los Angeles County Registrar results"
    site_name = "Los Angeles County Registrar-Recorder"
    url = "https://results.lavote.gov/"
    platform = "LA County results API"
    tiers = frozenset({4})

    def pull(self, fetch):
        listed = fetch.get(LA + "GetMenuElections", params={"year": config.ELECTION_DATE.year}).get("Data") or []
        election = next((e for e in listed if e["Date"][:10] == config.ELECTION_DATE.isoformat()), None)
        if not election:
            raise NotPublished(f"no {config.ELECTION_DATE} election listed")
        return parse_la(fetch.get(LA + "GetElectionData", params={"electionID": election["ID"]})["Data"])


def clarity_county(name: str) -> ClaritySource:
    return ClaritySource(f"ca.{name.lower().replace(' ', '_')}", "CA", f"{name} County (Clarity)",
                         f"{name} County", f"CA/{name.replace(' ', '_')}", tiers=(4,), level="county", county=name)


SOURCES = [
    LosAngeles(),
    LiveVoterTurnoutSource("ca.orange", "CA", "Orange", "https://ocvote.gov/results/current-election-results",
                           f"{config.ELECTION_DATE.year} General Election"),
    *[clarity_county(n) for n in ("Santa Clara", "Contra Costa", "Sonoma", "Ventura", "Marin")],
]
