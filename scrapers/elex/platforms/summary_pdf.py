"""Election-night "Election Summary" PDFs, the summary report many counties' tabulation software exports (Albany NY).
Text extracted with pdfplumber reads:

  Albany County Election Night Unofficial Results          <- page header, repeated
  2026 General Election 100% Precincts Reporting
  November 3, 2026
  Member of Assembly District 107                          <- contest title (may wrap)
  Vote For 1
  TOTAL VOTE % Election Early Absentee Affidavit
  Day Voting
  DEM Chloe E. Pierce 10,199 60.52% 3,896 5,695 608 0       <- one row per party line
  REP Scott H. Bendett 4,418 26.21% ...
  WFP Chloe E. Pierce 1,222 7.25% ...
  Write-In Totals 22 0.13% ...
  Total Votes Cast / Overvotes / Undervotes / Contest Totals
  Election Summary - 11/04/2026 1:29 AM Page 2 of 10       <- page footer

A candidate's party lines are combined into one choice with `party_lines`. Precincts reporting is countywide only.

The other layout, "Statement of Votes Cast" (Saratoga NY), is parsed by parse_statement:

  Governor/Lt Gov (Vote for 1)
  101758 ballots (50 over voted ballots, 50 overvotes, 1165 undervotes)
  204 precincts reported out of 204 total                  <- per contest
  Kathy C. Hochul 52541                                    <- candidate total
  Democratic 48656                                         <- then their party lines
  Working Families 3885
  Write-in 254 / Total 100543 / Overvotes 50 / Undervotes 1165
"""
import io
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

_VOTE_FOR = re.compile(r"^Vote For (\d+)$")
_ROW = re.compile(r"^(?:(?P<party>[A-Z]{2,5}) )?(?P<name>.+?) (?P<votes>[\d,]+) (?P<pct>[\d.]+)%")
_NOT_CANDIDATES = ("write-in", "total votes cast", "overvotes", "undervotes", "contest totals")
_FOOTER = re.compile(r"^Election Summary - ([\d/]+ [\d:]+ [AP]M)")


def pdf_text(data: bytes) -> str:
    import pdfplumber  # only this source needs it
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def parse(text: str, *, source_id: str, state: str, county: str, whole: frozenset = frozenset()) -> list[Contest]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header = set(lines[:3])
    stamp = next((m.group(1) for ln in lines if (m := _FOOTER.match(ln))), None)
    updated = datetime.strptime(stamp, "%m/%d/%Y %I:%M %p").isoformat() + "-05:00" if stamp else None
    pct = re.search(r"([\d.]+)% Precincts Reporting", text)
    reporting = (Reporting(as_percent=False, text=f"Countywide, {pct.group(1)}% of precincts reporting")
                 if pct else Reporting())
    contests, pending, current = [], [], None
    for line in lines:
        if line in header or _FOOTER.match(line) or line.startswith(("TOTAL VOTE %", "Day Voting")):
            continue
        if m := _VOTE_FOR.match(line):
            title = re.sub(r"\s+", " ", " ".join(pending)).strip()
            current = {"title": title, "vote_for": int(m.group(1)), "choices": {}}
            contests.append(current)
            pending = []
            continue
        if current is None:
            if line.startswith("Statistics"):
                pending = []
            elif not re.search(r"\d[\d,]* [\d,]+", line):  # statistics rows carry several numbers; titles one at most
                pending.append(line)
            continue
        if line.lower().startswith("contest totals"):
            current, pending = None, []
            continue
        row = _ROW.match(line)
        if not row or row.group("name").lower().startswith(_NOT_CANDIDATES):
            continue
        name, party, votes = row.group("name").strip(), row.group("party"), names.to_int(row.group("votes"))
        choice = current["choices"].setdefault(name, Choice(name, 0, None, choice_id=name, party_lines={}))
        choice.votes += votes
        code = names.party(party) if party else None
        if code:
            choice.party_lines[code] = choice.party_lines.get(code, 0) + votes
            if choice.party in (None, "WFP") and code != "WFP":
                choice.party = code
    out = []
    for item in contests:
        title = item["title"]
        is_measure = bool(re.match(r"(?i)(proposal|proposition)\b", title))
        kind = "measure" if is_measure else names.office_type(title)
        district = names.measure_id(title) if is_measure else names.district(title)
        complete = (kind in ("local", "judicial") and "supreme court" not in title.lower()) or (kind, district) in whole
        choices = list(item["choices"].values())
        if is_measure:
            choices = [Choice(names.yes_no(c.name), c.votes, choice_id=c.choice_id) for c in choices]
        contest = Contest(
            source=source_id, contest_id=title, state=state, title=title, office_type=kind, district=district,
            jurisdiction=f"{county} County", scope="complete" if complete else "partial", vote_for=item["vote_for"],
            reporting=reporting, feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        out.append(contest)
    return out


# Party-line rows in "Statement of Votes Cast" reports, which name the party in full.
PARTY_LINES = {"democratic": "DEM", "republican": "REP", "conservative": "CON", "working families": "WFP",
               "vote affordable": "VAF", "green": "GRN", "libertarian": "LIB", "independence": "IND",
               "safe affordable": "SAF", "freedom": "FRE"}
_STATEMENT_CONTEST = re.compile(r"^(.+?) \(Vote for (\d+)\)$")
_STATEMENT_ROW = re.compile(r"^(.+?) (\d+)$")
_STATEMENT_STOP = ("total", "overvotes", "undervotes")
# Each page repeats the report header, which can fall inside a contest.
_STATEMENT_HEADER = re.compile(r"^(Statement of Votes Cast|Total Ballots Cast|All Election Districts|Choice Votes|"
                               r"\S.* County, \d{4} )")


def _contest(title, vote_for, choices, *, source_id, state, county, reporting, updated, whole):
    is_measure = bool(re.search(r"(?i)\b(proposal|proposition|prop)\b", title))
    kind = "measure" if is_measure else names.office_type(title)
    if re.match(r"(?i)senator \d+(st|nd|rd|th) district", title):
        kind = "state_senate"  # Saratoga: "Senator 44th District"
    district = (names.measure_id(title) or names.fold(title)[:60]) if is_measure else names.district(title)
    complete = (kind in ("local", "judicial") and "supreme court" not in title.lower()) or (kind, district) in whole
    if is_measure:
        complete = not re.match(r"(?i)proposal (one|two|three|four|five|\d)\b", title)  # statewide proposals
        choices = [Choice(names.yes_no(c.name), c.votes, choice_id=c.choice_id) for c in choices]
    contest = Contest(
        source=source_id, contest_id=title, state=state, title=title, office_type=kind, district=district,
        jurisdiction=f"{county} County", scope="complete" if complete else "partial", vote_for=vote_for,
        reporting=reporting, feed_updated_at=updated, choices=choices)
    contest.fill_percentages()
    return contest


def parse_statement(text: str, *, source_id: str, state: str, county: str, whole: frozenset = frozenset()
                    ) -> list[Contest]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    stamp = re.search(r"(\d{4}-\d{2}-\d{2})\s.*?(\d{2}:\d{2}:\d{2})", text, re.S)
    updated = f"{stamp.group(1)}T{stamp.group(2)}-05:00" if stamp else None
    out, current = [], None

    def close():
        if current:
            out.append(_contest(current["title"], current["vote_for"], current["choices"], source_id=source_id,
                                state=state, county=county, reporting=current["reporting"], updated=updated,
                                whole=whole))

    for line in lines:
        if m := _STATEMENT_CONTEST.match(line):
            close()
            current = {"title": m.group(1).strip(), "vote_for": int(m.group(2)), "choices": [], "reporting": Reporting(),
                       "done": False, "last": None}
            continue
        if current is None or current["done"] or _STATEMENT_HEADER.match(line):
            continue
        if m := re.match(r"^(\d+) precincts reported out of (\d+) total$", line):
            if current["reporting"].units_total is None:  # the contest's own; later ones are page headers
                current["reporting"] = Reporting(int(m.group(1)), int(m.group(2)))
            continue
        row = _STATEMENT_ROW.match(line)
        if not row:
            continue
        label, votes = row.group(1).strip(), int(row.group(2))
        if label.lower() in _STATEMENT_STOP:
            current["done"] = True
            continue
        code = PARTY_LINES.get(label.lower())
        last = current["last"]
        lines_so_far = sum((last.party_lines or {}).values()) if last else 0
        if last is not None and not code and lines_so_far and lines_so_far + votes <= last.votes:
            code = label.upper()  # a minor party line ("No Kings") that still fits within the candidate's total
        if code and last is not None:
            last.party_lines = {**(last.party_lines or {}), code: votes}
            if last.party in (None, "WFP") and code != "WFP":
                last.party = code
            continue
        if label.lower().startswith("write-in"):
            current["last"] = None
            continue
        current["last"] = Choice(label, votes, None, choice_id=label)
        current["choices"].append(current["last"])
    close()
    return out


class SummaryPdfSource(Source):
    """`pdf_url` is the report's fixed address, or None to find it on `page_url` with `link` (a regex whose first
    group is a number; the highest wins, for counties that number each update: "...Unofficial09.pdf").
    `layout` is "summary" (parse) or "statement" (parse_statement)."""
    platform = "Election Summary PDF"
    level = "county"

    def __init__(self, id, state, county, pdf_url, page_url, site_name, *, link=None, layout="summary", tiers=(4,)):
        self.id, self.state, self.county, self.tiers = id, state, county, frozenset(tiers)
        self.title = f"{county} County election night results (PDF)"
        self.pdf_url, self.url, self.site_name, self.link, self.layout = pdf_url, page_url, site_name, link, layout

    def _find_pdf(self, fetch) -> str:
        if self.pdf_url:
            return self.pdf_url
        page = fetch.get(self.url, expect="text")
        found = {int(m.group(1)): m.group(0) for m in re.finditer(self.link, page)}
        if not found:
            raise NotPublished(f"no results PDF linked on {self.url}")
        return found[max(found)]

    def pull(self, fetch):
        pdf_url = self._find_pdf(fetch)
        text = pdf_text(fetch.get(pdf_url, expect="bytes"))
        when = config.ELECTION_DATE
        if when.strftime("%B %-d, %Y") not in text and when.strftime("%b %d, %Y") not in text:
            raise NotPublished(f"{pdf_url} isn't the {when} election")
        parser = parse_statement if self.layout == "statement" else parse
        contests = parser(text, source_id=self.id, state=self.state, county=self.county)
        for contest in contests:
            contest.url = pdf_url
        return contests
