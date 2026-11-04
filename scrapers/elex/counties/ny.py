"""New York county sources: NYC (below), Westchester (Enhanced Voting) and Erie (Results Caster); the last two are
configuration over their platform modules.

NYC's Board of Elections results (enr.boenyc.gov), static HTML pages:

  index.html            -> one link per office: OF<n>CY0PY<m>.html
  OF<n>CY0PY<m>.html    -> the office's district list, with an "Expand List" link (OFA<n>...) to every district's
                           results on one page; an office with one contest (Governor) shows its results here instead
  each contest          -> <th>Title<div>(Vote for one)</div></th>, then a row per party line ("Working Families"),
                           then "Totals by Candidate" when a candidate has several lines, "Percentage of Scanners
                           Reported", and "Information As Of"

A "*" after a title marks a contest that crosses the city line ("City of New York portion ... only"): statewide
offices, NY-3 and NY-16, SD-34 and SD-36. Those are partial and the matcher ignores them; NYC-only districts are
complete.
"""
import html
import re
from datetime import datetime

from .. import names
from ..model import Choice, Contest, Reporting
from ..platforms.enhanced_voting import EnhancedVotingSource
from ..platforms.resultscaster import ResultsCasterSource
from ..source import NotPublished, Source

NYC = "https://enr.boenyc.gov/"

_CONTEST = re.compile(r"<th>([^<]+)<div[^>]*>\(([^)]*)\)</div></th>")
_ROW = re.compile(r"<tr><td >\d+</td><td>&nbsp;</td><td >(.*?)</td><td >(.*?)</td>"
                  r"<td align=\"right\" >(.*?)</td><td align=\"right\" >(.*?)</td>", re.S)


def _clean(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cell))).strip()


def _as_of(chunk: str) -> str | None:
    m = re.search(r"Information As Of:\s*([\d-]+ [\d:]+)", chunk)
    if not m:
        return None
    # NYC posts Eastern time; -05:00 is EST, which is in effect on election night.
    return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").isoformat() + "-05:00"


def parse(page: str, source_id: str = "ny.nyc") -> list[Contest]:
    contests = []
    heads = list(_CONTEST.finditer(page))
    for i, head in enumerate(heads):
        chunk = page[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(page)]
        raw_title = _clean(head.group(1))
        partial = raw_title.endswith("*")
        title = raw_title.rstrip("*").strip()
        lines, _, totals = chunk.partition("Totals by Candidate")
        # Each candidate's votes per party line, then one total per candidate. A candidate on one line has no
        # totals section; their line is their total.
        by_name: dict[str, Choice] = {}
        for name, party, votes, _pct in _ROW.findall(lines):
            name, code, n = _clean(name), names.party(_clean(party)), names.to_int(_clean(votes))
            if name.upper() == "WRITE-IN" and not n:
                continue
            choice = by_name.setdefault(name, Choice(name, 0, code, choice_id=name, party_lines={}))
            choice.votes += n
            if code:
                choice.party_lines[code] = choice.party_lines.get(code, 0) + n
                if choice.party in (None, "WFP") and code != "WFP":
                    choice.party = code  # show the main line ("DEM"), not WFP's fusion line
        for name, _party, votes, _pct in _ROW.findall(totals):
            name = _clean(name)
            if name in by_name:
                by_name[name].votes = names.to_int(_clean(votes))
        scanners = re.search(r"Percentage of Scanners Reported:.*?([\d.]+)\s*%", chunk, re.S)
        scanners_pct = names.to_float(scanners.group(1)) if scanners else None
        is_measure = title.lower().startswith("proposal")
        kind = "measure" if is_measure else names.office_type(title)
        contest = Contest(
            source=source_id, contest_id=title, state="NY", title=title, office_type=kind,
            district=names.measure_id(title) if is_measure else names.district(title),
            jurisdiction="New York City", scope="partial" if partial else "complete",
            vote_for=names.vote_for(head.group(2)) or 1,
            reporting=Reporting(pct=scanners_pct, text=None if scanners_pct is None
                                else f"{scanners_pct:g}% of scanners reported"),
            feed_updated_at=_as_of(chunk),
            choices=[Choice(names.yes_no(c.name), c.votes, c.party, choice_id=c.choice_id,
                            party_lines=c.party_lines) if is_measure else c for c in by_name.values()])
        contest.fill_percentages()
        contests.append(contest)
    return contests


class NewYorkCity(Source):
    id = "ny.nyc"
    state = "NY"
    level = "county"
    county = "NYC"
    title = "NYC Board of Elections ENR"
    site_name = "NYC Board of Elections"
    url = NYC
    platform = "NYC BOE ENR (HTML)"
    tiers = frozenset({1, 2, 3, 4})

    def pull(self, fetch):
        index = fetch.get(NYC, expect="text")
        if "NOVEMBER 3, 2026" not in index.upper():
            raise NotPublished("NYC's results page isn't showing Nov 3 yet")
        contests, seen = [], set()
        for office in dict.fromkeys(re.findall(r'href="(OF\d+CY0PY\d+\.html)"', index)):
            page = fetch.get(NYC + office, expect="text")
            expanded = re.search(r'href="(OFA[^"]+\.html)"', page)
            if expanded:
                page = fetch.get(NYC + expanded.group(1), expect="text")
            for contest in parse(page, self.id):
                if contest.contest_id not in seen:
                    seen.add(contest.contest_id)
                    contests.append(contest)
        return contests


SOURCES = [
    NewYorkCity(),
    # Westchester's results are on Enhanced Voting's shared host (westchestercountyny.gov/boe99 links there).
    EnhancedVotingSource("ny.westchester", "NY", "Westchester County (Enhanced Voting)",
                         "Westchester County Board of Elections", "https://app.enhancedvoting.com",
                         "westchester-county-ny", tiers=(4,), level="county", county="Westchester"),
    ResultsCasterSource("ny.erie", "NY", "Erie", "erie", "Erie County Board of Elections"),
]
