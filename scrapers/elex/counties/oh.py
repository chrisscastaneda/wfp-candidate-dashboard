"""Ohio county sources beyond Hamilton (Clarity, in states/clarity_states.py).

Franklin County (vote.franklincountyohio.gov/elections) is a map app over one JSON file:

  /elections/api/election/live
      -> {name, year, month, day, isTest, isOfficial, turnout: [{area, reg, abs, day, prov}],
          races: [{id, name ("#8 Proposed Charter Amendment (By Petition) City of Columbus"), level (f/s/c/l),
                   choices: [{name ("Dem Amy Acton"), party, votes: [per area], abs: [per area], ...}]}]}

`votes` is each precinct's total (absentee included); `abs` is the absentee part. Local issues are numbered with "#"
(Columbus's Issue 8 is "#8 ..."). The county's Live Voter Turnout page (liveresults.franklincountyohio.gov, election
4) is only a test page pointing back here.
"""
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

FRANKLIN = "https://vote.franklincountyohio.gov/elections/"
_PARTY_PREFIX = re.compile(r"^(Dem|Rep|Lib|Grn|Ind|Non) ", re.I)


def _total(value) -> int:
    return sum(value) if isinstance(value, list) else names.to_int(value)


def parse_franklin(data: dict) -> list[Contest]:
    ballots = sum((a.get("abs") or 0) + (a.get("day") or 0) + (a.get("prov") or 0) for a in data.get("turnout") or [])
    reporting = Reporting(as_percent=False, text=f"Countywide: {ballots:,} ballots counted") if ballots else Reporting()
    contests = []
    for race in data.get("races") or []:
        title = re.sub(r"\s+", " ", race["name"]).strip()
        number = re.match(r"#(\d+[A-Za-z]?)\s+", title)
        is_measure = bool(number) or race.get("level") == "l" and not race.get("office")
        kind = "measure" if is_measure else names.office_type(title)
        if race.get("level") == "c" and kind not in ("judicial", "measure"):
            kind = "local"
        choices = []
        for c in race.get("choices") or []:
            name = c["name"].strip()
            votes = _total(c.get("votes"))
            if name.lower().startswith("write-in") and not votes:
                continue
            label = names.yes_no(name) if is_measure else _PARTY_PREFIX.sub("", name)
            choices.append(Choice(label, votes, names.party(c.get("party")) if c.get("party") else None,
                                  choice_id=name))
        # Statewide, federal and district races are only Franklin's share; county and local ones are whole.
        share = race.get("level") in ("f", "s") or kind in ("federal_house", "state_house", "state_senate")
        contest = Contest(
            source="oh.franklin", contest_id=str(race.get("id")), state="OH", title=title, office_type=kind,
            district=(number.group(1).lower() if number else names.fold(title)[:60]) if is_measure
            else names.district(title), jurisdiction="Franklin County", scope="partial" if share else "complete",
            reporting=reporting, url=FRANKLIN, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Franklin(Source):
    id = "oh.franklin"
    state = "OH"
    level = "county"
    county = "Franklin"
    title = "Franklin County Board of Elections live results"
    site_name = "Franklin County Board of Elections"
    url = FRANKLIN
    platform = "Franklin County results API (JSON)"
    tiers = frozenset({4})

    def pull(self, fetch):
        data = fetch.get(FRANKLIN + "api/election/live")
        day = (data.get("year"), data.get("month"), data.get("day"))
        if data.get("isTest") or day != (config.ELECTION_DATE.year, config.ELECTION_DATE.month,
                                         config.ELECTION_DATE.day):
            raise NotPublished(f"Franklin's live results are for {day} (test={data.get('isTest')}), not "
                               f"{config.ELECTION_DATE}")
        return parse_franklin(data)


SOURCES = [Franklin()]
