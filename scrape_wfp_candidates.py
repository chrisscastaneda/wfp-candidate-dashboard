#!/usr/bin/env python3
"""Scrape endorsed candidates and ballot measures from https://workingfamilies.org/candidates/.

The page shows the first 10 candidates per state; the rest are loaded by the
"View More" button through WordPress admin-ajax (action=more_candidates).
This script fetches both, adds each state's ballot measures, classifies every
office, then writes candidates.csv and candidates.json.

Usage: python3 scrape_wfp_candidates.py [output_dir]
Standard library only.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

PAGE_URL = "https://workingfamilies.org/candidates/"
AJAX_URL = "https://workingfamilies.org/wp-admin/admin-ajax.php"
UA = "Mozilla/5.0 (compatible; wfp-candidate-scraper/1.0)"

CELL_FIELDS = {
    "state-cands__name": "name",
    "state-cands__info": "office",
    "state-cands__rac": "region",
}
DISTRICT_RE = re.compile(
    r"\b((?:Legislative |Congressional |Council |Senate |House |Assembly )?"
    r"(?:District|Ward|Trustee Area|Area|Seat|Position|Precinct|Zone|Division|Subdistrict)"
    r"\s+(?:\d[\w-]*|[A-Z])|[Aa]t[- ][Ll]arge|Citywide|Countywide)\b"
)

# --- Office classification -------------------------------------------------
# Categories and the level each belongs to. Judicial is State or Local
# depending on the court (see classify_office).
FEDERAL_SENATE = "Federal Senate"
FEDERAL_HOUSE = "Federal House"
STATE_EXECUTIVE = "State Executive"
STATE_SENATE = "State Senate"
STATE_HOUSE = "State House"
JUDICIAL = "Judicial"
LOCAL_OFFICE = "Local Office"
BALLOT_MEASURE = "Ballot Measure"

STATE_NAMES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|"
    "District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|"
    "Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|"
    "Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|"
    "North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|"
    "South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|"
    "West Virginia|Wisconsin|Wyoming"
)
# Optional "<State name>" and/or "State" (incl. the site's "Sate" typo) prefix.
STATE_PREFIX = rf"^(?:(?:{STATE_NAMES})\s+)?(?:S(?:t)?ate\s+)?"

FEDERAL_SENATE_RE = re.compile(r"^U\.?\s?S\.?\s+Senat", re.I)
FEDERAL_HOUSE_RE = re.compile(r"^(?:U\.?\s?S\.?\s+(?:House|Representative|Congress)|Congress)", re.I)
STATE_SENATE_RE = re.compile(STATE_PREFIX + r"Senat(?:e|or)\b", re.I)
STATE_HOUSE_RE = re.compile(
    STATE_PREFIX + r"(?:House|Assembly|Representative|Assembly\s?member|Delegate)\b", re.I
)
# Statewide offices; the whole office (minus a trailing ", District ...") must be
# one of these, so "Cook County Treasurer" or "City Attorney" stay local.
STATE_EXECUTIVE_RE = re.compile(
    STATE_PREFIX
    + r"(?:Governor|Lt\.?\s+Governor|Lieutenant\s+Governor|Secretary\s+of\s+State|"
    r"Attorney\s+General|Treasurer|Comptroller|Controller|Auditor(?:\s+of\s+State)?|"
    r"Superintendent\s+of\s+Public\s+Instruction|(?:Labor|Insurance|Land|Agriculture)\s+Commissioner|"
    r"Commissioner\s+of\s+(?:Public\s+Lands|Labor|Insurance|Agriculture)|"
    r"Corporation\s+Commission(?:er)?|Public\s+Service\s+Commission(?:er)?|"
    r"Railroad\s+Commission(?:er)?|Board\s+of\s+Education|Board\s+of\s+Regents|"
    r"University\s+(?:of\s+\w+\s+)?Regents?)"
    r"(?:\s*,.*)?$",
    re.I,
)
JUDICIAL_RE = re.compile(
    r"\b(?:Court|Judge|Justice|Magistrate|District\s+Attorney|State[’']?s\s+Attorney|County\s+Attorney|"
    r"Prosecut\w*|Public\s+Defender|Solicitor\s+General)\b",
    re.I,
)
# Only statewide courts count as State; trial courts and prosecutors are Local.
STATE_COURT_RE = re.compile(r"\b(?:Supreme\s+Court|Court\s+of\s+Appeals?|Appeals\s+Court|Appellate)\b", re.I)
# Non-judicial offices that contain judicial words ("Clerk of Courts").
NOT_JUDICIAL_RE = re.compile(r"\bClerk\b", re.I)
# Words that mark an office as municipal/county even if it has a statewide-sounding title.
LOCAL_MARKER_RE = re.compile(
    r"\b(?:City|County|Town|Township|Village|Borough|Parish|Municipal|Mayor|Council|"
    r"School|Unified|USD|Community\s+College)\b",
    re.I,
)
# "Board of Education" without "State" is a county/school board, not the state board.
STATE_BOARD_NEEDS_STATE_RE = re.compile(r"^(?:Board\s+of\s+Education|Board\s+of\s+Regents)", re.I)

def classify_office(office):
    """Return (office_category, office_level) for an office title."""
    o = office.strip()
    if FEDERAL_SENATE_RE.search(o):
        return FEDERAL_SENATE, "Federal"
    if FEDERAL_HOUSE_RE.search(o):
        return FEDERAL_HOUSE, "Federal"
    if JUDICIAL_RE.search(o) and not NOT_JUDICIAL_RE.search(o):
        level = "State" if STATE_COURT_RE.search(o) and not LOCAL_MARKER_RE.search(o) else "Local"
        return JUDICIAL, level
    if not LOCAL_MARKER_RE.search(o):
        if STATE_SENATE_RE.search(o):
            return STATE_SENATE, "State"
        if STATE_HOUSE_RE.search(o):
            return STATE_HOUSE, "State"
        if STATE_EXECUTIVE_RE.search(o) and not STATE_BOARD_NEEDS_STATE_RE.search(o):
            return STATE_EXECUTIVE, "State"
    return LOCAL_OFFICE, "Local"


def fetch(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


class CandidatesParser(HTMLParser):
    """Collects state sections, the candidate rows in their tables, and their
    ballot measure lists (<dt> measure name, <dd> Yes/No)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.states = []  # dicts: slug, name, wfp_url, ajax_id, rows, measures
        self.rows = []    # rows when parsing an AJAX fragment (no state wrapper)
        self._in_hed = False
        self._cell = None
        self._row = None
        self._dl_tag = None   # "dt" or "dd" while inside one in a state's list
        self._dl_big = False  # the <dt> is a section heading, not a measure
        self._dl_text = ""

    @property
    def _current_rows(self):
        return self.states[-1]["rows"] if self.states else self.rows

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "li" and "nlist__item--state" in classes:
            slug = next((c[len("nlist__item--"):] for c in classes
                         if c.startswith("nlist__item--") and c != "nlist__item--state"), "")
            self.states.append({"slug": slug, "name": "", "wfp_url": "", "ajax_id": None,
                                "rows": [], "measures": []})
        elif tag == "h1" and "nlist__hed" in classes:
            self._in_hed = True
        elif tag == "a" and "nlist__hed-link" in classes and self.states:
            self.states[-1]["wfp_url"] = a.get("href", "")
        elif tag == "button" and "nlist__more-link" in classes and self.states:
            self.states[-1]["ajax_id"] = a.get("data-state-id")
        elif tag == "tr":
            self._row = {}
        elif tag == "td" and self._row is not None:
            field = next((CELL_FIELDS[c] for c in classes if c in CELL_FIELDS), None)
            if field:
                self._cell = field
                self._row[field] = ""
        elif tag in ("dt", "dd") and self.states and (
                "nlist__name" in classes or "nlist__info" in classes):
            self._dl_tag = tag
            self._dl_text = ""
            if tag == "dt":
                self._dl_big = "nlist__name--big" in classes

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_hed = False
        elif tag == "td":
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row.get("name"):
                self._current_rows.append({k: clean(v) for k, v in self._row.items()})
            self._row = None
        elif tag == self._dl_tag:
            text = clean(self._dl_text)
            measures = self.states[-1]["measures"]
            if tag == "dt" and not self._dl_big and text:
                measures.append({"name": text, "position": ""})
            elif tag == "dd" and not self._dl_big and measures and not measures[-1]["position"]:
                measures[-1]["position"] = text
            self._dl_tag = None

    def handle_data(self, data):
        if self._in_hed and self.states:
            self.states[-1]["name"] += data
        elif self._cell and self._row is not None:
            self._row[self._cell] += data
        elif self._dl_tag:
            self._dl_text += data


def parse_district(office):
    m = DISTRICT_RE.search(office)
    return m.group(1) if m else ""


def record(name, office, category, level, position, district, state, region=""):
    return {
        "name": name,
        "office": office,
        "office_category": category,
        "office_level": level,
        "is_federal": level == "Federal",
        "is_state": level == "State",
        "is_local": level == "Local",
        "position": position,
        "district": district,
        "state": clean(state["name"]),
        "state_slug": state["slug"],
        "region": region,
        "state_wfp_page": state["wfp_url"],
        "source_url": PAGE_URL,
    }


def scrape():
    parser = CandidatesParser()
    parser.feed(fetch(PAGE_URL))

    for state in parser.states:
        if state["ajax_id"]:
            frag = CandidatesParser()
            frag.feed(fetch(AJAX_URL, {
                "action": "more_candidates",
                "state": state["ajax_id"],
                "count": len(state["rows"]),
            }))
            state["rows"].extend(frag.rows)
            time.sleep(0.5)  # be polite

    records = []
    for state in parser.states:
        heading_region = ""
        for row in state["rows"]:
            office = row.get("office", "")
            if not office:
                # A row with no office is a region heading (e.g. New York's
                # "Long Island"); it applies to the rows that follow it.
                heading_region = row["name"]
                continue
            category, level = classify_office(office)
            records.append(record(row["name"], office, category, level, "Endorsed",
                                  parse_district(office), state,
                                  row.get("region") or heading_region))
    for state in parser.states:
        for m in state["measures"]:
            records.append(record(m["name"], "Ballot Measure", BALLOT_MEASURE, "Ballot",
                                  m["position"], "", state))
    for i, r in enumerate(records, 1):
        r["id"] = i
    return [{"id": r.pop("id"), **r} for r in records]


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    records = scrape()

    fields = list(records[0].keys())
    with open(out_dir / "candidates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({k: str(v).lower() if isinstance(v, bool) else v for k, v in r.items()})

    counts = {}
    for r in records:
        counts[r["office_category"]] = counts.get(r["office_category"], 0) + 1
    payload = {
        "source": PAGE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(records),
        "counts_by_category": counts,
        "candidates": records,
    }
    with open(out_dir / "candidates.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(records)} records to {out_dir.resolve()}")
    for category, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {category:<16} {n}")


if __name__ == "__main__":
    main()
