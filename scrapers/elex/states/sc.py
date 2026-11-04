"""South Carolina Election Commission results (scvotes.gov). On election night 2026 the state's Clarity site listed
no election; instead scvotes.gov/<year>-general-election-results/ links a new XLSX snapshot every 15–30 minutes:

  /wp-content/uploads/2026/11/2026-11-03-1130PM-General-Election-Results.xlsx   (listed oldest first)

The workbook has a "Table of Contents", "Registered Voters", then one sheet per contest:
  row 1    "U.S.  House of Representatives, District  4 (Vote For 1)"
  row 2    each candidate's name ("DEM Jane Doe") above its block of seven vote-type columns, the last "Total Votes"
  rows     one per county, then "Total:"
The files give no precincts-reporting count. Read with the standard library (an XLSX is zipped XML).
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from .. import config, names
from ..model import Choice, Contest
from ..source import NotPublished, Source

PAGE = "https://scvotes.gov/{year}-general-election-results/"
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_PARTY = re.compile(r"^(DEM|REP|UNC|GRN|LIB|CON|ALN|WFM|LAB|IND|AMR|PET)\s+")


def _column(ref: str) -> int:
    """'AE2' -> 30 (0-based)."""
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(data: bytes) -> dict[str, list[dict[int, str]]]:
    """Sheet name -> rows, each row a {column index: text} map."""
    book = zipfile.ZipFile(io.BytesIO(data))
    shared = [''.join(t.text or "" for t in si.iter(_NS + "t"))
              for si in ET.fromstring(book.read("xl/sharedStrings.xml")).findall(_NS + "si")]
    sheet_names = [s.get("name") for s in ET.fromstring(book.read("xl/workbook.xml")).find(_NS + "sheets")]
    sheets = {}
    for i, name in enumerate(sheet_names, start=1):
        rows = []
        for row in ET.fromstring(book.read(f"xl/worksheets/sheet{i}.xml")).iter(_NS + "row"):
            cells = {}
            for cell in row.findall(_NS + "c"):
                value = cell.find(_NS + "v")
                if value is None:
                    continue
                cells[_column(cell.get("r"))] = shared[int(value.text)] if cell.get("t") == "s" else value.text
            rows.append(cells)
        sheets[name] = rows
    return sheets


def parse(sheets: dict[str, list[dict[int, str]]], updated: str | None = None) -> list[Contest]:
    contests = []
    for name, rows in sheets.items():
        if name in ("Table of Contents", "Registered Voters") or len(rows) < 3:
            continue
        heading = re.sub(r"\s+", " ", rows[0].get(0, "")).strip()
        vote_for = re.search(r"\(Vote For (\d+)\)", heading)
        title = re.sub(r"\s*\(Vote For \d+\)\s*$", "", heading)
        totals = next((r for r in rows if (r.get(0) or "").strip().lower().startswith("total")), None)
        if not title or totals is None:
            continue
        choices = []
        for col, label in sorted(rows[1].items()):
            label = re.sub(r"\s+", " ", label).strip()
            if not label or label.lower().startswith("write-in"):
                continue
            m = _PARTY.match(label)
            choices.append(Choice(label[m.end():] if m else label, names.to_int(totals.get(col + 6)),
                                  names.party(m.group(1)) if m else None, choice_id=label))
        kind = names.office_type(title)
        contest = Contest(
            source="sc", contest_id=title, state="SC", title=title, office_type=kind, district=names.district(title),
            jurisdiction="South Carolina", vote_for=int(vote_for.group(1)) if vote_for else 1,
            feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


def snapshot_time(url: str) -> str | None:
    """'...2026-11-03-1130PM-General...' -> '2026-11-03T23:30:00-05:00'. "12AM" on the 3rd is midnight going into the
    4th, the way the Commission names it."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})-(\d{1,2})(\d{2})?-?([AP]M)", url)
    if not m:
        return None
    day = datetime.strptime(m.group(1), "%Y-%m-%d")
    hour, minute = int(m.group(2)) % 12 + (12 if m.group(4) == "PM" else 0), int(m.group(3) or 0)
    if m.group(4) == "AM" and int(m.group(2)) == 12:
        day += timedelta(days=1)
    return day.replace(hour=hour, minute=minute).isoformat() + "-05:00"


class SouthCarolina(Source):
    id = "sc"
    state = "SC"
    title = "SC Election Commission results (XLSX snapshots)"
    site_name = "SC Election Commission"
    platform = "SC XLSX snapshots"
    tiers = frozenset({1, 2})
    url = PAGE.format(year=config.ELECTION_DATE.year)

    def pull(self, fetch):
        page = fetch.get(self.url, expect="text")
        stamp = config.ELECTION_DATE.isoformat()
        links = list(dict.fromkeys(re.findall(rf'https://scvotes\.gov/wp-content/uploads/[^"\']*/{stamp}-'
                                              rf'[^"\']*General-Election-Results[^"\']*\.xlsx', page)))
        if not links:
            raise NotPublished(f"no {stamp} results file linked on {self.url}")
        latest = links[-1]  # the page lists snapshots oldest first
        return parse(read_xlsx(fetch.get(latest, expect="bytes")), updated=snapshot_time(latest))


SOURCES = [SouthCarolina()]
