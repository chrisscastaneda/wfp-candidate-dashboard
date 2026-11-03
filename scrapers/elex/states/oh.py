"""Ohio Secretary of State live results (liveresults.ohiosos.gov), a Knockout app over a JSON API:

  /Api/v1/Contest/getContestList            -> groups of contests, each with a contestObjectId
  /Api/v1/Contest/GetContestDetailsObject   -> one contest, broken down by county (contestName, contestObjectId)

There's no statewide total, so each contest is the sum of its counties. That's one request per contest (about 160),
so config.HOST_GAPS spaces them a quarter second apart. The site lists only state and federal contests; county
races (Hamilton County) come from county sources.
"""
from collections import OrderedDict

from .. import names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

API = "https://liveresults.ohiosos.gov/Api/v1/Contest/"


def parse(detail: dict) -> Contest:
    title = detail.get("contestDisplayName") or detail["contestName"]
    is_measure = "issue" in title.lower()
    totals: dict[str, Choice] = OrderedDict()
    reported = total = 0
    for county in detail.get("contestList") or []:
        reported += county.get("reportedPrecincts") or 0
        total += county.get("totalPrecincts") or 0
        for cand in county.get("candidatesRunning") or []:
            name = cand.get("primaryCandidate") or ""
            if cand.get("runningMate"):
                name = f"{name} and {cand['runningMate']}"
            choice = totals.setdefault(name, Choice(names.yes_no(name) if is_measure else name, 0,
                                                    names.party(cand.get("candidateParty")), choice_id=name))
            choice.votes += int(cand.get("vCount") or 0)
    # Write-ins with no votes are noise in a two-candidate race.
    choices = [c for c in totals.values() if c.votes or not _is_write_in(detail, c.choice_id)]
    contest = Contest(
        source="oh", contest_id=detail.get("contestId") or title, state="OH", title=title,
        office_type="measure" if is_measure else names.office_type(title),
        district=names.measure_id(title.replace("State Issue", "Issue")) if is_measure else names.district(title)
        if "District" in title else None,
        jurisdiction="Ohio", reporting=Reporting(reported, total), choices=choices)
    contest.fill_percentages()
    return contest


def _is_write_in(detail: dict, name: str) -> bool:
    for county in detail.get("contestList") or []:
        for cand in county.get("candidatesRunning") or []:
            full = cand.get("primaryCandidate", "") + (f" and {cand['runningMate']}" if cand.get("runningMate")
                                                       else "")
            if full == name:
                return bool(cand.get("isWriteIn"))
    return False


class Ohio(Source):
    id = "oh"
    state = "OH"
    title = "Ohio SoS live results"
    platform = "OH live results API"
    tiers = frozenset({1, 2, 3})
    local_races = False

    def pull(self, fetch):
        groups = fetch.get(API + "getContestList")
        if not groups:
            raise NotPublished("no contests listed")
        contests = []
        for group in groups:
            for item in group.get("contestGroupings") or []:
                detail = fetch.get(API + "GetContestDetailsObject", params={
                    "contestName": item["contestName"], "contestObjectId": item["contestObjectId"],
                    "resultsLevel": "", "countyId": ""})
                contests.append(parse(detail))
        return contests


SOURCES = [Ohio()]
