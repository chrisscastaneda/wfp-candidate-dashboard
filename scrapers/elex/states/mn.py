"""Minnesota Secretary of State results files (electionresultsfiles.sos.mn.gov/<yyyymmdd>/<file>.txt), listed on
electionresults.sos.mn.gov's "Media Files" page. Semicolon-delimited, no header, one row per candidate:

  MN;27;;0405;County Attorney;;9003;Cedrick Frazier;;;NP;395;395;257445;50.55;509255
  state; county code; precinct; office id; office; district; candidate id; name; suffix; incumbent; party;
  precincts reporting; precincts total; votes; percent; contest total votes

County codes are the counties in alphabetical order (19 Dakota, 27 Hennepin). WFP's Minnesota endorsements are county
races, so only cntyRaces.txt is read; statewide and legislative files can be added the same way.
"""
from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import Source

COUNTIES = [
    "Aitkin", "Anoka", "Becker", "Beltrami", "Benton", "Big Stone", "Blue Earth", "Brown", "Carlton", "Carver", "Cass",
    "Chippewa", "Chisago", "Clay", "Clearwater", "Cook", "Cottonwood", "Crow Wing", "Dakota", "Dodge", "Douglas",
    "Faribault", "Fillmore", "Freeborn", "Goodhue", "Grant", "Hennepin", "Houston", "Hubbard", "Isanti", "Itasca",
    "Jackson", "Kanabec", "Kandiyohi", "Kittson", "Koochiching", "Lac qui Parle", "Lake", "Lake of the Woods",
    "Le Sueur", "Lincoln", "Lyon", "McLeod", "Mahnomen", "Marshall", "Martin", "Meeker", "Mille Lacs", "Morrison",
    "Mower", "Murray", "Nicollet", "Nobles", "Norman", "Olmsted", "Otter Tail", "Pennington", "Pine", "Pipestone",
    "Polk", "Pope", "Ramsey", "Red Lake", "Redwood", "Renville", "Rice", "Rock", "Roseau", "St. Louis", "Scott",
    "Sherburne", "Sibley", "Stearns", "Steele", "Stevens", "Swift", "Todd", "Traverse", "Wabasha", "Wadena", "Waseca",
    "Washington", "Watonwan", "Wilkin", "Winona", "Wright", "Yellow Medicine",
]
assert len(COUNTIES) == 87


def parse(text: str, *, source_id: str = "mn", url: str | None = None) -> list[Contest]:
    contests: dict[tuple, Contest] = {}
    for line in text.splitlines():
        f = line.split(";")
        if len(f) < 16 or f[0] != "MN":
            continue
        county = COUNTIES[int(f[1]) - 1] if f[1].isdigit() and 0 < int(f[1]) <= len(COUNTIES) else f[1]
        office, district = f[4].strip(), f[5].strip()
        key = (f[1], f[3], district)
        contest = contests.get(key)
        if contest is None:
            title = f"{county} {office}" if office.startswith("County ") else f"{county} County {office}"
            contest = contests[key] = Contest(
                source=source_id, contest_id="-".join(key), state="MN", title=title, office_type="local",
                district=names.district(title) or district or None, jurisdiction=f"{county} County",
                reporting=Reporting(names.to_int(f[11]), names.to_int(f[12])), url=url, choices=[])
        name = " ".join(p for p in (f[7].strip(), f[8].strip()) if p)
        votes = names.to_int(f[13])
        if f[10] == "WI" or name.upper() == "WRITE-IN":
            if not votes:
                continue
            name = "Write-in"
        contest.choices.append(Choice(name, votes, names.party(f[10]) if f[10] not in ("NP", "WI") else None,
                                      choice_id=f[6]))
    out = list(contests.values())
    for contest in out:
        contest.fill_percentages()
    return out


class Minnesota(Source):
    id = "mn"
    state = "MN"
    title = "Minnesota SoS results files"
    site_name = "Minnesota Secretary of State"
    url = "https://electionresults.sos.mn.gov/"
    platform = "MN SoS media files (text)"
    tiers = frozenset({4})

    @property
    def files_url(self) -> str:
        return f"https://electionresultsfiles.sos.mn.gov/{config.ELECTION_DATE:%Y%m%d}/"

    def pull(self, fetch):
        # Files sit under the election date, so an answer is this election's results.
        url = self.files_url + "cntyRaces.txt"
        return parse(fetch.get(url, expect="text"), url=url)


SOURCES = [Minnesota()]
