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
import xml.etree.ElementTree as ET
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..platforms.enhanced_voting import EnhancedVotingSource
from ..platforms.resultscaster import ResultsCasterSource
from ..platforms.nts_vic import NtsVicSource
from ..platforms.summary_pdf import SummaryPdfSource
from ..source import NotPublished, Source

NYC = "https://enr.boenyc.gov/"

_CONTEST = re.compile(r"<th>([^<]+)<div[^>]*>\(([^)]*)\)</div></th>")
# The leading row's cells carry style="font-weight: bold"; the others are a bare "<td >".
_ROW = re.compile(r"<tr><td[^>]*>\d+</td><td>&nbsp;</td><td[^>]*>(.*?)</td><td[^>]*>(.*?)</td>"
                  r"<td align=\"right\"[^>]*>(.*?)</td><td align=\"right\"[^>]*>(.*?)</td>", re.S)


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


# Chautauqua County's results site (enr.chqvotes.com) is a page that reads one XML file, Default_3_0.xml:
#   <election timestamp="11/3/2026 10:03:35 PM" date="Tuesday, November 3, 2026" ...>
#   areatypes/admindivision[@name="Town"]/area[@id, @name="Town of Busti"]
#   offices/office/contests/contest[@id, @name="Town Supervisor", @areaid]/choices/choice[@id, @name]/aff[@id]
#   parties/party[@id, @abbrev]; simpleresults/ch[@id, @v]; contestoverview/co[@c, @n (seats)]
#   progress[@closed, @total] (tabulators, countywide)
# State and district races are filed under the "New York State" area and are the county's share.
CHAUTAUQUA = "https://enr.chqvotes.com/"
_PLACE_AREAS = {"Town", "Town Ward", "Village", "City", "City Ward"}


def parse_chautauqua(xml: bytes | str) -> list[Contest]:
    root = ET.fromstring(xml)
    areas = {a.get("id"): (d.get("name"), a.get("name").strip())
             for d in root.find("areatypes") for a in d}
    parties = {p.get("id"): p.get("abbrev") for p in root.find("parties")}
    votes = {ch.get("id"): names.to_int(ch.get("v")) for ch in root.find("simpleresults")}
    seats = {co.get("c"): names.to_int(co.get("n")) for co in root.find("contestoverview")}
    stamp = root.get("timestamp")
    updated = (datetime.strptime(stamp, "%m/%d/%Y %I:%M:%S %p").isoformat() + "-05:00") if stamp else None
    progress = root.find("progress")
    closed, total = (names.to_int(progress.get("closed")), names.to_int(progress.get("total"))) \
        if progress is not None else (None, None)
    contests = []
    for item in root.iter("contest"):
        kind_of_area, area = areas.get(item.get("areaid"), ("", ""))
        title = re.sub(r"\s+", " ", item.get("name")).strip()
        if kind_of_area in _PLACE_AREAS:
            title = f"{title}, {area}"  # "Town Supervisor, Town of Kiantone"
        choices = []
        for choice in item.iter("choice"):
            name = re.sub(r"\s+", " ", choice.get("name")).strip()
            n = votes.get(choice.get("id"), 0)
            if choice.get("isw") == "True" and not n:
                continue
            affs = [parties.get(a.get("id")) for a in choice.findall("aff")]
            choices.append(Choice(name, n, names.party(affs[0]) if affs and affs[0] else None,
                                  choice_id=choice.get("id")))
        kind = names.office_type(title)
        if kind_of_area != "State" and kind not in ("local", "judicial"):
            kind = "local"  # "County Sheriff", "Town Clerk"
        contest = Contest(
            source="ny.chautauqua", contest_id=item.get("id"), state="NY", title=title, office_type=kind,
            district=names.district(title), jurisdiction="Chautauqua County",
            scope="partial" if kind_of_area == "State" else "complete", vote_for=seats.get(item.get("id")) or 1,
            reporting=Reporting(closed, total, as_percent=False,
                                text=f"Countywide, {closed} of {total} poll sites reported") if total else Reporting(),
            feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Chautauqua(Source):
    id = "ny.chautauqua"
    state = "NY"
    level = "county"
    county = "Chautauqua"
    title = "Chautauqua County election night results"
    site_name = "Chautauqua County Board of Elections"
    url = CHAUTAUQUA
    platform = "Chautauqua ENR (XML)"
    tiers = frozenset({4})

    def pull(self, fetch):
        data = fetch.get(CHAUTAUQUA + "Default_3_0.xml", expect="bytes")
        when = config.ELECTION_DATE.strftime("%B %-d, %Y")
        if when.encode() not in data:
            raise NotPublished(f"Chautauqua's results file isn't the {when} election")
        return parse_chautauqua(data)


# Nassau County posts election-night results as a PDF converted to HTML (app.nassaucountyny.gov/BOE/results/
# election2.html): every word is a positioned text element. Joined in order, the text reads
#   "Member of Assembly District 9 (Vote for 1) Christopher J. Walis 4140 27.59% Michael A. Durso 10861 72.38%
#    Republican9979 Conservative882 Write-in5 0.03% Total15006100.00%"
# Each candidate is "Name votes pct%", followed by their party lines ("Democratic9516 Working Families 558"). Every
# page repeats a header ("Page: 1 of 9 Unofficial Results ... ChoiceVotes Vote %"), which is cut out first.
NASSAU = "https://app.nassaucountyny.gov/BOE/results/election2.html"
_NASSAU_HEADER = re.compile(r"(Page: \d+ of \d+ )?Unofficial Results .*?ChoiceVotes Vote %( All Precincts)?", re.S)
_NASSAU_CONTEST = re.compile(r"([A-Z][^()%]*?) \(Vote for (\d+)\)")
_NASSAU_CHOICE = re.compile(r"([A-Z\u00c0-\u017f][A-Za-z\u00c0-\u017f.'\u2019\- ]*?) ?(\d+) (\d+\.\d+)%")
_NASSAU_LINE = re.compile(r"([A-Z][A-Za-z ]+?) ?(\d+)(?= |$)")


def nassau_text(page: str) -> str:
    page = re.sub(r"<style.*?</style>", "", page, flags=re.S)
    runs = re.findall(r"<(?:tspan|text|span|div)[^>]*>([^<]{1,200})<", page)
    return re.sub(r"\s+", " ", " ".join(html.unescape(r).strip() for r in runs if r.strip()))


def parse_nassau(text: str) -> list[Contest]:
    precincts = re.search(r"(\d+) precincts reported out of (\d+) total", text)
    stamp = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text)
    updated = stamp.group(0).replace(" ", "T") + "-05:00" if stamp else None
    reporting = (Reporting(int(precincts.group(1)), int(precincts.group(2)), as_percent=False,
                           text=f"Countywide, {precincts.group(1)} of {precincts.group(2)} precincts reported")
                 if precincts else Reporting())
    body = _NASSAU_HEADER.sub(" ", text)
    heads = list(_NASSAU_CONTEST.finditer(body))
    contests = []
    for i, head in enumerate(heads):
        chunk = body[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(body)]
        chunk = chunk.split(" Total", 1)[0]
        title = head.group(1).strip()
        found = list(_NASSAU_CHOICE.finditer(chunk))
        choices = []
        for j, m in enumerate(found):
            name = m.group(1).strip()
            if name.lower().startswith("write-in"):
                continue
            lines_text = chunk[m.end():found[j + 1].start() if j + 1 < len(found) else len(chunk)]
            lines = {names.party(p.strip()): int(v) for p, v in _NASSAU_LINE.findall(lines_text)}
            lines = {k: v for k, v in lines.items() if k}
            party = next((k for k in lines if k != "WFP"), next(iter(lines), None))
            choices.append(Choice(name, int(m.group(2)), party, choice_id=name, party_lines=lines or None))
        is_measure = bool(re.match(r"(?i)(proposal|proposition)", title))
        kind = "measure" if is_measure else names.office_type(title)
        contest = Contest(
            source="ny.nassau", contest_id=title, state="NY", title=title, office_type=kind,
            district=names.measure_id(title) if is_measure else names.district(title), jurisdiction="Nassau County",
            scope="complete" if kind in ("local", "measure") else "partial", vote_for=int(head.group(2)),
            reporting=reporting, feed_updated_at=updated, url=NASSAU,
            choices=[Choice(names.yes_no(c.name), c.votes, choice_id=c.choice_id) for c in choices] if is_measure
            else choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Nassau(Source):
    id = "ny.nassau"
    state = "NY"
    level = "county"
    county = "Nassau"
    title = "Nassau County election night results"
    site_name = "Nassau County Board of Elections"
    url = NASSAU
    platform = "Nassau results (PDF as HTML)"
    tiers = frozenset({4})

    def pull(self, fetch):
        page = fetch.get(NASSAU, expect="text")
        text = nassau_text(page)
        if len(text) < 1000 and page.count("<path") > 100:
            # From Nov 10 the page draws its words as vector shapes, with no text to read. That's unreadable, not
            # "no election", so it's an error and the last good results are kept (and still count in district sums).
            raise ValueError("Nassau's results page has no text (words drawn as vector paths); keeping last results")
        when = config.ELECTION_DATE.strftime("%B %-d, %Y")
        if f"{when} General Election" not in text:
            raise NotPublished(f"Nassau's results page isn't the {when} general election")
        return parse_nassau(text)


# Schenectady County's election-night page (schenectadycountyny.gov/sites/default/files/BOE Election Results/GE26.html,
# named for the election: GE26, PE26 ...) is a "Summary Results Report" exported as HTML. As text, one line each:
#   Vote For 1 / Member of Assembly District 110 / DEM Phillip G. Steck / 8,415 / WOR Phillip G. Steck / 901 /
#   Write-In Totals / 17 / TOTAL
# Each candidate's party lines are combined. Precincts reporting is countywide only.
SCHENECTADY = "https://www.schenectadycountyny.gov/sites/default/files/BOE%20Election%20Results/"
_PARTY_CODE = re.compile(r"^([A-Z]{2,4}) (?=[A-Z][a-z])")


def html_lines(page: str) -> list[str]:
    page = re.sub(r"<(style|script).*?</\1>", "", page, flags=re.S | re.I)
    page = re.sub(r"<br\s*/?>|</(tr|p|div|h\d|td|th)>", "\n", page, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    return [ln for ln in (re.sub(r"\s+", " ", raw).strip() for raw in text.split("\n")) if ln]


def parse_schenectady(lines: list[str]) -> list[Contest]:
    joined = "\n".join(lines)
    precincts = re.search(r"Election Day Precincts Reporting\n(\d+) of (\d+)", joined)
    reporting = (Reporting(int(precincts.group(1)), int(precincts.group(2)), as_percent=False,
                           text=f"Countywide, {precincts.group(1)} of {precincts.group(2)} precincts reporting")
                 if precincts else Reporting())
    contests, i = [], 0
    while i < len(lines):
        vote_for = re.match(r"^Vote For (\d+)$", lines[i])
        if not vote_for or i + 1 >= len(lines):
            i += 1
            continue
        title, i = lines[i + 1], i + 2
        by_name: dict[str, Choice] = {}
        while i + 1 < len(lines) and lines[i] != "TOTAL" and not lines[i].startswith("Write-In"):
            label, votes = lines[i], lines[i + 1]
            if not re.fullmatch(r"[\d,]+", votes):
                break
            m = _PARTY_CODE.match(label)
            name = label[m.end():] if m else label
            code = names.party(m.group(1)) if m else None
            choice = by_name.setdefault(name, Choice(name, 0, None, choice_id=name, party_lines={}))
            choice.votes += names.to_int(votes)
            if code:
                choice.party_lines[code] = choice.party_lines.get(code, 0) + names.to_int(votes)
                if choice.party in (None, "WFP") and code != "WFP":
                    choice.party = code
            i += 2
        is_measure = bool(re.match(r"(?i)(proposal|proposition)\b", title))
        kind = "measure" if is_measure else names.office_type(title)
        choices = list(by_name.values())
        if is_measure:
            choices = [Choice(names.yes_no(c.name), c.votes, choice_id=c.choice_id) for c in choices]
        complete = kind in ("local",) or (kind == "judicial" and "supreme court" not in title.lower())
        contest = Contest(
            source="ny.schenectady", contest_id=title, state="NY", title=title, office_type=kind,
            district=names.measure_id(title) if is_measure else names.district(title),
            jurisdiction="Schenectady County", scope="complete" if complete else "partial",
            vote_for=int(vote_for.group(1)), reporting=reporting, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Schenectady(Source):
    id = "ny.schenectady"
    state = "NY"
    level = "county"
    county = "Schenectady"
    title = "Schenectady County election night results"
    site_name = "Schenectady County Board of Elections"
    platform = "Summary Results Report (HTML)"
    tiers = frozenset({4})

    @property
    def url(self) -> str:
        return f"{SCHENECTADY}GE{config.ELECTION_DATE.year % 100:02d}.html"

    def pull(self, fetch):
        lines = html_lines(fetch.get(self.url, expect="text"))
        when = config.ELECTION_DATE.strftime("%B %-d, %Y")
        if when not in lines[:10]:
            raise NotPublished(f"{self.url} isn't the {when} election")
        return parse_schenectady(lines)


# Counties whose Nov 3 results are on Enhanced Voting's shared host, at <name>-county-ny. Found by probing the
# jurisdictions API for all 62 counties (Nov 4, 2026); Onondaga (Results Caster), Chautauqua, Niagara, Albany, Saratoga,
# Nassau and Schenectady aren't there.
_EV_COUNTIES = ("Orange", "Monroe", "Broome", "Oneida", "Rockland", "Clinton", "Suffolk", "Putnam", "Rensselaer",
                "Columbia", "Cattaraugus", "Chemung", "Dutchess", "Ulster", "Sullivan",
                # No WFP local races; their shares complete multi-county districts (combine.py).
                "Jefferson", "Livingston", "Madison", "Ontario", "Steuben", "Wayne")


def ev_county(name: str) -> EnhancedVotingSource:
    return EnhancedVotingSource(f"ny.{name.lower()}", "NY", f"{name} County (Enhanced Voting)",
                                f"{name} County Board of Elections", "https://app.enhancedvoting.com",
                                f"{name.lower()}-county-ny", tiers=(4,), level="county", county=name)


SOURCES = [
    NewYorkCity(),
    # Westchester's results are on Enhanced Voting's shared host (westchestercountyny.gov/boe99 links there).
    EnhancedVotingSource("ny.westchester", "NY", "Westchester County (Enhanced Voting)",
                         "Westchester County Board of Elections", "https://app.enhancedvoting.com",
                         "westchester-county-ny", tiers=(4,), level="county", county="Westchester"),
    ResultsCasterSource("ny.erie", "NY", "Erie", "erie", "Erie County Board of Elections"),
    # onondaga.gov/elections links its election-night results to ongov.resultscaster.com.
    ResultsCasterSource("ny.onondaga", "NY", "Onondaga", "ongov", "Onondaga County Board of Elections"),
    *[ev_county(name) for name in _EV_COUNTIES],
    Chautauqua(),
    Nassau(),
    Schenectady(),
    # Albany's results page (albanycountyny.gov/electionresults) adds its PDF links with JavaScript, so the
    # election-night PDF's address is set here. A re-upload under a new address needs this updated.
    SummaryPdfSource("ny.albany", "NY", "Albany",
                     "https://content.civicplus.com/api/assets/ny-albanycounty/b7449722-a131-4e24-9399-df0d7963cb54",
                     "https://www.albanycountyny.gov/electionresults", "Albany County Board of Elections"),
    # Saratoga numbers each election-night upload (BoE-GeneralElection2026-Unofficial09.pdf); the highest is newest.
    SummaryPdfSource("ny.saratoga", "NY", "Saratoga", None,
                     "https://www.saratogacountyny.gov/departments/board-of-elections/",
                     "Saratoga County Board of Elections", layout="statement",
                     link=r"https://www\.saratogacountyny\.gov/wp/wp-content/uploads/\d{4}/\d{2}/"
                          rf"BoE-GeneralElection{config.ELECTION_DATE.year}-Unofficial(\d+)\.pdf"),
    # Niagara moved from ny.votereporting.com (403 to scripts) to NTS; elections.niagaracounty.gov/election-results
    # links election 297 for Nov 3, 2026.
    NtsVicSource("ny.niagara", "NY", "Niagara", 297, "Niagara County Board of Elections"),
]
