"""California Secretary of State returns API (api.sos.ca.gov/returns). JSON per office; no election ID, since it
always serves the current election. Statewide offices, Congress, legislature, Board of Equalization and props.
No local races: those come from county sources.
"""
import re

from .. import names
from ..model import Choice, Contest, Reporting
from ..source import Source

API = "https://api.sos.ca.gov/returns/"

# Feed path -> office type. District feeds return a list of contests; statewide feeds return one.
FEEDS = {
    "governor": "governor",
    "lieutenant-governor": "lt_governor",
    "secretary-of-state": "secretary_of_state",
    "controller": "controller",
    "treasurer": "treasurer",
    "attorney-general": "attorney_general",
    "insurance-commissioner": "insurance_commissioner",
    "superintendent-of-public-instruction": "superintendent",
    "us-rep/district/all": "federal_house",
    "state-senate/district/all": "state_senate",
    "state-assembly/district/all": "state_house",
    "board-of-equalization/district/all": "board_of_equalization",
    "ballot-measures": "measure",
}


def parse_reporting(text: str | None) -> Reporting:
    # "12.5% (2,983 of 23,860) precincts reporting"
    m = re.search(r"([\d.]+)%\s*\(([\d,]+) of ([\d,]+)\)", text or "")
    if not m:
        return Reporting(text=text)
    return Reporting(names.to_int(m.group(2)), names.to_int(m.group(3)), float(m.group(1)), text)


def parse(path: str, payload) -> list[Contest]:
    office_type = FEEDS[path]
    if office_type == "measure":
        reporting = parse_reporting(payload.get("Reporting"))
        return [Contest(
            source="ca", contest_id=f"prop/{int(m['Number'])}", state="CA", title=f"Proposition {int(m['Number'])}: "
            f"{m['Name']}", office_type="measure", district=str(int(m["Number"])), jurisdiction="California",
            reporting=reporting, feed_updated_at=payload.get("ReportingTime"),
            choices=[Choice("Yes", names.to_int(m["yesVotes"]), pct=names.to_float(m["yesPercent"])),
                     Choice("No", names.to_int(m["noVotes"]), pct=names.to_float(m["noPercent"]))],
        ) for m in payload["ballot-measures"]]
    contests = []
    for race in payload if isinstance(payload, list) else [payload]:
        title = race["raceTitle"].split(" - ")[0]
        district = names.district(title) if "/district/" in path else None
        contests.append(Contest(
            source="ca", contest_id=f"{path.split('/')[0]}/{district}" if district else path, state="CA",
            title=title, office_type=office_type, district=district, jurisdiction="California",
            reporting=parse_reporting(race.get("Reporting")), feed_updated_at=race.get("ReportingTime"),
            choices=[Choice(c["Name"], names.to_int(c["Votes"]), names.party(c.get("Party")),
                            names.to_float(c.get("Percent"))) for c in race["candidates"]],
        ))
    return contests


class California(Source):
    id = "ca"
    state = "CA"
    title = "California SoS returns API"
    platform = "CA SoS API"
    tiers = frozenset({1, 2, 3})
    local_races = False

    def pull(self, fetch):
        contests = []
        for path in FEEDS:
            contests += parse(path, fetch.get(API + path))
        return contests


SOURCES = [California()]
