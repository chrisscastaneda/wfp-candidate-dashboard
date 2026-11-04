"""NTS "Voter Information Center" election-night results (vic.ntsdata.com/enr/<County>/<electionId>/result), used by
Niagara County NY. The page is an app over a public JSON API at vicapi.azurewebsites.net/api:

  SummaryResult/getenrelectiondetails?countyId=<County>&electionId=<id>
      -> description, textDate ("11/03/2026 00:00:00"), updatedDate, totalPollingDist,
         electionDayMessage / earlyVotingMessage / absenteeMessage ("Fully Reported", "Partially Reported")
  SummaryResult/getresult?countyId=<County>&electionId=<id>
      -> {"oldContest": [{contestId, name, choices: [{choiceId, choiceName, ppAbb ("DEM", "WOR"), totalVot}]}]}
         one choice row per party line; "contest" lists the same contests without choices

The list of a county's elections needs a login, so the election id is set per source (Niagara's Nov 3, 2026 general
is 297) and checked against the election's date on each pull.
"""
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

API = "https://vicapi.azurewebsites.net/api/SummaryResult/"


def parse(details: dict, result: dict, *, source_id: str, state: str, county: str) -> list[Contest]:
    updated = details.get("updatedDate")
    updated_at = updated + "-05:00" if updated and "+" not in updated and not updated.endswith("Z") else updated
    parts = [f"election day {details.get('electionDayMessage', '').lower()}",
             f"absentees {details.get('absenteeMessage', '').lower()}"]
    reporting = Reporting(as_percent=False, text="Countywide: " + ", ".join(p for p in parts if not p.endswith(" ")))
    contests = []
    for item in result.get("oldContest") or []:
        title = re.sub(r"\s+", " ", item["name"]).strip()
        # "Representative in Congress 23rd District - CD 23": the trailing code repeats the district.
        title = re.sub(r"\s+-\s+(CD|SD|AD|LD)\s+\d+$", "", title)
        is_measure = bool(re.match(r"(?i)(proposal|proposition)\b", title))
        kind = "measure" if is_measure else names.office_type(title)
        by_id: dict[int, Choice] = {}
        for row in item.get("choices") or []:
            name, votes, code = row["choiceName"].strip(), names.to_int(row.get("totalVot")), row.get("ppAbb")
            if name.lower().startswith("write-in") and not votes:
                continue
            choice = by_id.setdefault(row["choiceId"], Choice(names.yes_no(name) if is_measure else name, 0, None,
                                                               choice_id=str(row["choiceId"]), party_lines={}))
            choice.votes += votes
            party = names.party(code) if code else None
            if party:
                choice.party_lines[party] = choice.party_lines.get(party, 0) + votes
                if choice.party in (None, "WFP") and party != "WFP":
                    choice.party = party
        complete = kind == "local" or (kind == "judicial" and "supreme court" not in title.lower()) or is_measure
        contest = Contest(
            source=source_id, contest_id=str(item["contestId"]), state=state, title=title, office_type=kind,
            district=names.measure_id(title) if is_measure else names.district(title),
            jurisdiction=f"{county} County", scope="complete" if complete else "partial", reporting=reporting,
            feed_updated_at=updated_at, choices=list(by_id.values()))
        contest.fill_percentages()
        contests.append(contest)
    return contests


class NtsVicSource(Source):
    platform = "NTS Voter Information Center"
    level = "county"

    def __init__(self, id, state, county, election_id, site_name, tiers=(4,)):
        self.id, self.state, self.county, self.tiers = id, state, county, frozenset(tiers)
        self.election_id, self.site_name = election_id, site_name
        self.title = f"{county} County (NTS results)"
        self.url = f"https://vic.ntsdata.com/enr/{county}/{election_id}/result"

    def pull(self, fetch):
        params = {"countyId": self.county, "electionId": self.election_id}
        details = fetch.get(API + "getenrelectiondetails", params=params)
        when = (details.get("textDate") or "").split()[0]
        try:
            day = datetime.strptime(when, "%m/%d/%Y").date()
        except ValueError:
            day = None
        if day != config.ELECTION_DATE:
            raise NotPublished(f"{self.county} election {self.election_id} is dated {when or 'nothing'}, not "
                               f"{config.ELECTION_DATE}")
        return parse(details, fetch.get(API + "getresult", params=params), source_id=self.id, state=self.state,
                     county=self.county)
