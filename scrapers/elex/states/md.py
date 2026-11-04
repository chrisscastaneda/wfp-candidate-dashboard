"""Maryland State Board of Elections results (elections.maryland.gov/elections/<year>/general_results/), static HTML:

  index (the folder)                              links to every office page and county page
  gen_results_<year>_6_<n>.html                   one House of Delegates district ("33B"), whole-district totals
  gen_results_<year>_by_county_<n>.html           every contest on one county's ballot (counties numbered
                                                  alphabetically: Baltimore County 4, Montgomery 16, ...)

Each contest is an <h2> office (plus an <h3> district on office pages), "Vote for N", "(x of y election day
precincts reported)" and a table of Name, Party, four vote-type columns, Total, Percentage ("NR" before results).
County pages repeat their share of state and federal contests; those are marked partial.
"""
import html
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://elections.maryland.gov/elections/{year}/general_results/"

DELEGATE_DISTRICTS = ["33B"]
# County page numbers for counties with WFP county races.
COUNTIES = {"Baltimore County": 4, "Frederick": 11, "Howard": 14, "Montgomery": 16, "Prince George's": 17}

_ROW = re.compile(r"<tr>\s*<td><div>(.*?)</div></td>\s*<td>(.*?)</td>(.*?)</tr>", re.S)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse(page: str, *, jurisdiction: str, county_page: bool, id_prefix: str) -> list[Contest]:
    contests = []
    office = sub = heading_vote_for = ""
    # Walk headings in order: <h2> is the office, an <h3> that isn't "Vote for N" is the district under it
    # (one office can have several), and each table that follows is one contest.
    for n, part in enumerate(re.split(r"(<h2>.*?</h2>|<h3>.*?</h3>)", page, flags=re.S)):
        if part.startswith("<h2>"):
            office, sub, heading_vote_for = _text(part), "", ""
            continue
        if part.startswith("<h3>"):
            if "vote for" in part.lower():
                heading_vote_for = part  # county pages put "Vote for N" in an <h3>; office pages in an <h4>
            else:
                sub = _text(part)
            continue
        if "<table" not in part or not office:
            continue
        title = f"{office} {sub}".strip()
        vote_for = re.search(r"Vote for (?:up to )?(\d+)", part) or re.search(r"Vote for (?:up to )?(\d+)",
                                                                                  heading_vote_for)
        reported = re.search(r"\(([\d,]+) of ([\d,]+) election day precincts reported\)", part)
        choices = []
        for name, party, cells in _ROW.findall(part):
            name = _text(name)
            if name in ("Totals", "Other Write-Ins") or not name:
                continue
            total = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", cells, re.S)]
            votes = total[-2] if len(total) >= 2 else "0"
            choices.append(Choice(name, 0 if votes == "NR" else names.to_int(votes), names.party(_text(party))))
        if not choices:
            continue
        is_measure = {c.name for c in choices} <= {"For", "Against", "Yes", "No"}
        kind = "measure" if is_measure else names.office_type(title)
        if is_measure:
            for c in choices:
                c.name = c.choice_id = names.yes_no(c.name)
        contest = Contest(
            source="md", contest_id=f"{id_prefix}/{title}", state="MD", title=title, office_type=kind,
            # "District 33B" -> "33": the matcher compares district numbers; the surname picks the subdistrict.
            district=names.measure_id(title) if is_measure else names.district(title),
            jurisdiction=jurisdiction,
            scope="partial" if county_page and kind not in ("local", "judicial", "measure") else "complete",
            vote_for=int(vote_for.group(1)) if vote_for else 1,
            reporting=Reporting(names.to_int(reported.group(1)), names.to_int(reported.group(2)))
            if reported else Reporting(), choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Maryland(Source):
    id = "md"
    state = "MD"
    title = "Maryland State Board of Elections results"
    site_name = "Maryland State Board of Elections"
    url = BASE.format(year=config.ELECTION_DATE.year)
    platform = "MD SBE results pages (HTML)"
    tiers = frozenset({2, 4})

    def pull(self, fetch):
        base = BASE.format(year=config.ELECTION_DATE.year)
        index = fetch.get(base, expect="text")
        pages = {_text(label): href for href, label in
                 re.findall(r'href="(gen_results_\d+_6_\d+\.html)"[^>]*>(.*?)</a>', index, re.S)}
        if not pages:
            raise NotPublished("no House of Delegates pages listed")
        contests = []
        for district in DELEGATE_DISTRICTS:
            if district not in pages:
                raise NotPublished(f"House of Delegates district {district} not listed")
            contests += parse(fetch.get(base + pages[district], expect="text"), jurisdiction="Maryland",
                              county_page=False, id_prefix=f"hod-{district}")
        for county, n in COUNTIES.items():
            page = fetch.get(f"{base}gen_results_{config.ELECTION_DATE.year}_by_county_{n}.html", expect="text")
            contests += parse(page, jurisdiction=f"{county} County".replace("County County", "County"),
                              county_page=True, id_prefix=f"county-{n}")
        return contests


SOURCES = [Maryland()]
