"""District of Columbia Board of Elections results (electionresults.dcboe.org). The page is a React app over JSON:

  /electionResults/getElectionInfo/<slug>   -> ElectionDate, LastUpdated, PrecinctsCounted, TotalPrecincts,
                                              RCVAvailableDate ("November 4, 2026")
  /cityWide/getCityWide/<slug>              -> [{OfficeName, ContestNumber, IsRCV, ElectionData: [{Contestant
                                              ("DEM Robert White"), Votes, PartyCode}]}], every contest citywide

<slug> is "<year>-General-Election". DC uses ranked-choice voting for most offices from 2026. On election night only
first-choice counts are posted (round-by-round results follow later), so those contests say so in their title.

The shadow U.S. Senator and Representative aren't seats in Congress; they're filed as local offices so they can't
match a WFP U.S. House listing. The Delegate is DC's member of the House.
"""
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://electionresults.dcboe.org/"
_WARDS = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8"}
_NOT_CANDIDATES = {"OVER VOTES", "UNDER VOTES"}


def _office(title: str) -> tuple[str, str | None]:
    upper = title.upper()
    if upper.startswith("DELEGATE TO THE HOUSE"):
        return "federal_house", None
    if upper.startswith("ATTORNEY GENERAL"):
        return "attorney_general", None
    if upper.startswith(("INITIATIVE", "REFERENDUM", "CHARTER AMENDMENT")):
        return "measure", names.measure_id(title) or names.fold(title)[:60]
    ward = re.match(r"WARD (\w+) ", upper)
    return "local", _WARDS.get(ward.group(1)) if ward else None


def parse(info: dict, contests: list[dict]) -> list[Contest]:
    updated = info.get("LastUpdated")
    reporting = Reporting(info.get("PrecinctsCounted"), info.get("TotalPrecincts"))
    out = []
    for item in contests:
        title = re.sub(r"\s+", " ", item["OfficeName"]).strip()
        kind, district = _office(title)
        choices = []
        for row in item.get("ElectionData") or []:
            label = re.sub(r"\s+", " ", row["Contestant"]).strip()
            if label.upper() in _NOT_CANDIDATES or (label.lower() == "write-in" and not row.get("Votes")):
                continue
            code = row.get("PartyCode")
            if code and label.startswith(code + " "):
                label = label[len(code) + 1:]
            if kind == "measure":
                label = names.yes_no(label)
            choices.append(Choice(label, names.to_int(row.get("Votes")),
                                  names.party(code) if code and code != "NPN" else None,
                                  choice_id=str(row.get("CandidateNumber"))))
        if item.get("IsRCV"):
            title += " (first-choice votes)"
        contest = Contest(
            source="dc", contest_id=str(item["ContestNumber"]), state="DC", title=title, office_type=kind,
            district=district, jurisdiction="District of Columbia", reporting=reporting, feed_updated_at=updated,
            choices=choices)
        contest.fill_percentages()
        out.append(contest)
    return out


class DistrictOfColumbia(Source):
    id = "dc"
    state = "DC"
    title = "DC Board of Elections results"
    site_name = "DC Board of Elections"
    platform = "DCBOE results (JSON)"
    tiers = frozenset({1, 2, 3, 4})

    @property
    def slug(self) -> str:
        return f"{config.ELECTION_DATE.year}-General-Election"

    @property
    def url(self) -> str:
        return f"{BASE}election_results/{self.slug}"

    def pull(self, fetch):
        info = fetch.get(f"{BASE}electionResults/getElectionInfo/{self.slug}")
        if (info.get("ElectionDate") or "")[:10] != config.ELECTION_DATE.isoformat():
            raise NotPublished(f"DCBOE's {self.slug} isn't the {config.ELECTION_DATE} election")
        return parse(info, fetch.get(f"{BASE}cityWide/getCityWide/{self.slug}"))


SOURCES = [DistrictOfColumbia()]
