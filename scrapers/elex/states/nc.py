"""North Carolina State Board of Elections ENR. One JSON array per file, one row per candidate:

  er.ncsbe.gov/enr/<YYYYMMDD>/data/results_0.txt     every statewide, federal, legislative and judicial contest
  er.ncsbe.gov/enr/<YYYYMMDD>/data/results_<n>.txt   county n (alphabetical, 1-100): adds county races

The county files also repeat the county's share of statewide contests; those are skipped.
"""
from collections import OrderedDict

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import Source

BASE = "https://er.ncsbe.gov/enr/{date}/data/results_{n}.txt"

# Counties with WFP endorsements in county races: Alamance (sheriff), Durham (DA), Mecklenburg (sheriff).
COUNTIES = {1: "Alamance", 32: "Durham", 60: "Mecklenburg"}

_GROUP_TYPES = {"NCS": "state_senate", "NCH": "state_house"}


def parse(rows: list[dict], *, jurisdiction: str, skip_titles=frozenset()) -> list[Contest]:
    contests: dict[str, Contest] = OrderedDict()
    for row in rows:
        title = row["cnm"].split(" (VOTE FOR")[0].strip()
        if title in skip_titles:
            continue
        contest = contests.get(title)
        if contest is None:
            kind = _GROUP_TYPES.get(row.get("ogl")) or names.office_type(title)
            contest = contests[title] = Contest(
                source="nc", contest_id=f"{row.get('gid') or ''}:{title}", state="NC", title=title.title(),
                office_type=kind, district=names.district(title), jurisdiction=jurisdiction,
                vote_for=names.to_int(row.get("vfr")) or 1,
                reporting=Reporting(names.to_int(row.get("prt")), names.to_int(row.get("ptl"))))
        contest.choices.append(Choice(row["bnm"], names.to_int(row["vct"]), names.party(row.get("pty"))))
    for contest in contests.values():
        contest.fill_percentages()
    return list(contests.values())


class NorthCarolina(Source):
    id = "nc"
    state = "NC"
    title = "NC State Board of Elections ENR"
    site_name = "NC State Board of Elections"
    url = "https://er.ncsbe.gov/"
    platform = "NCSBE ENR JSON"
    tiers = frozenset({1, 2, 4})

    def pull(self, fetch):
        date = config.ELECTION_DATE.strftime("%Y%m%d")
        statewide = fetch.get(BASE.format(date=date, n=0))
        contests = parse(statewide, jurisdiction="North Carolina")
        seen = frozenset(r["cnm"].split(" (VOTE FOR")[0].strip() for r in statewide)
        for n, county in COUNTIES.items():
            contests += parse(fetch.get(BASE.format(date=date, n=n)), jurisdiction=f"{county} County",
                              skip_titles=seen)
        return contests


SOURCES = [NorthCarolina()]
