"""Oregon Secretary of State results (results.oregonvotes.gov). Same vendor as New Mexico and Nebraska, but
Oregon's CSV export is turned off and its export buttons are ASP.NET postbacks, so this reads the results pages:

  resultsSW.aspx?type=<GROUP>&map=CTY          statewide groups: FED, SWPAR, SENATE, HOUSE, SWNON, MCR, LMEA
  ResultsSW.aspx?type=CTYALL&cty=<n>&map=CTY   one county's ballot (ids from ResultsList.aspx)

The House page shows districts 1-30; districts 31-60 come from posting the page's form back with its "31 - 60"
button, the same request a browser makes when that button is clicked.

Each contest is a "display-results-box-a" block: a title, "N out of M Precincts Reported", then one block per
choice (name, party, votes). County pages repeat their share of statewide contests; those are skipped.
Multnomah County races are ranked-choice: these pages show first-choice totals only.
"""
import html
import re

from .. import names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://results.oregonvotes.gov"
GROUPS = ["FED", "SWPAR", "SENATE", "HOUSE", "SWNON", "MCR", "LMEA"]

# County results-page ids, for counties with WFP county or city races.
COUNTIES = {"Benton": "13", "Clackamas": "23", "Clatsop": "36", "Deschutes": "10", "Jackson": "03", "Lane": "09",
            "Marion": "21", "Multnomah": "26", "Polk": "19", "Washington": "28", "Yamhill": "22"}

# Page group -> form buttons that load the rest of the group, posted back to the same page.
MORE_PAGES = {"HOUSE": ["ctl00$MainContent$btnHouse4"]}

_CHOICE = re.compile(r'display-results-box-d">\s*(?:<[^h][^>]*>\s*)*<h1>(.*?)</h1>\s*<h2[^>]*>(.*?)</h2>'
                     r'.*?display-results-box-f">\s*<div>([\d,]*)</div>', re.S)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def form_fields(page: str) -> dict:
    """The page's hidden ASP.NET fields (__VIEWSTATE and friends), needed to post the form back."""
    return {html.unescape(name): html.unescape(value) for name, value in
            re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page)}


def parse(page: str, *, jurisdiction: str, skip_titles=frozenset()) -> list[Contest]:
    contests = []
    for block in re.split(r'<div class="display-results-box-a">', page)[1:]:
        title_html = re.search(r"<h1>(.*?)</h1>", block, re.S).group(1)
        # County pages link shared races as "<title> All Results"; Multnomah's add "- view results at <link>".
        title = re.sub(r"\s+All Results$", "", _text(re.split(r"\s+-\s+view results at", title_html)[0]))
        if names.fold(title) in skip_titles:
            continue
        race = re.search(r'raceid="(\d+)"', block) or re.search(r'id="chk-(\d+)"', block)
        reported = re.search(r"([\d,]+) out of ([\d,]+) Precincts", block)
        rows = [(_text(n), _text(p), names.to_int(v)) for n, p, v in _CHOICE.findall(block)]
        number = re.match(r"(\d{2}-\d+)\b", title)
        is_measure = bool(number) or {n for n, _, _ in rows} <= {"Yes", "No"}
        kind = "measure" if is_measure else names.office_type(title)
        choices = []
        for name, party, votes in rows:
            if name == "Write-in" and not votes:
                continue
            # Fusion nominations read "Democrat, Working Families" with one vote total; keep the first party.
            choices.append(Choice(name, votes, names.party(party.split(",")[0]) if party else None))
        contest = Contest(
            source="or", contest_id=race.group(1) if race else title, state="OR", title=title, office_type=kind,
            district=(number.group(1) if number else names.measure_id(title)) if is_measure
            else names.district(title), jurisdiction=jurisdiction,
            reporting=Reporting(names.to_int(reported.group(1)), names.to_int(reported.group(2)))
            if reported else Reporting(), choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Oregon(Source):
    id = "or"
    state = "OR"
    title = "Oregon SoS results"
    site_name = "Oregon Secretary of State"
    url = "https://results.oregonvotes.gov/"
    platform = "OR results pages (HTML)"
    tiers = frozenset({1, 2, 4})

    def pull(self, fetch):
        contests = []
        for group in GROUPS:
            params = {"type": group, "map": "CTY"}
            page = fetch.get(f"{BASE}/resultsSW.aspx", params=params, expect="text")
            contests += parse(page, jurisdiction="Oregon")
            for button in MORE_PAGES.get(group, []):
                buttons = re.findall(rf'name="{re.escape(button)}" value="([^"]*)"', page)
                more = fetch.post(f"{BASE}/resultsSW.aspx", {**form_fields(page), button: buttons[0].strip()},
                                  params=params)
                contests += parse(more, jurisdiction="Oregon")
        if not contests:
            raise NotPublished("results pages have no contests")
        seen = frozenset(names.fold(c.title) for c in contests)
        for county, cty in COUNTIES.items():
            page = fetch.get(f"{BASE}/ResultsSW.aspx", params={"type": "CTYALL", "cty": cty, "map": "CTY"},
                             expect="text")
            contests += parse(page, jurisdiction=f"{county} County", skip_titles=seen)
        return contests


SOURCES = [Oregon()]
