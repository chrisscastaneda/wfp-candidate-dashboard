#!/usr/bin/env python3
"""Scrape endorsed candidates from https://workingfamilies.org/candidates/.

The page shows the first 10 candidates per state; the rest are loaded by the
"View More" button through WordPress admin-ajax (action=more_candidates).
This script fetches both, then writes candidates.csv and candidates.json.

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


def fetch(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


class CandidatesParser(HTMLParser):
    """Collects state sections and the candidate rows in their tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.states = []  # dicts: slug, name, wfp_url, ajax_id, rows
        self.rows = []    # rows when parsing an AJAX fragment (no state wrapper)
        self._in_hed = False
        self._cell = None
        self._row = None

    @property
    def _current_rows(self):
        return self.states[-1]["rows"] if self.states else self.rows

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "li" and "nlist__item--state" in classes:
            slug = next((c[len("nlist__item--"):] for c in classes
                         if c.startswith("nlist__item--") and c != "nlist__item--state"), "")
            self.states.append({"slug": slug, "name": "", "wfp_url": "", "ajax_id": None, "rows": []})
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

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_hed = False
        elif tag == "td":
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row.get("name"):
                self._current_rows.append({k: clean(v) for k, v in self._row.items()})
            self._row = None

    def handle_data(self, data):
        if self._in_hed and self.states:
            self.states[-1]["name"] += data
        elif self._cell and self._row is not None:
            self._row[self._cell] += data


def parse_district(office):
    m = DISTRICT_RE.search(office)
    return m.group(1) if m else ""


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

    candidates = []
    for state in parser.states:
        for row in state["rows"]:
            office = row.get("office", "")
            candidates.append({
                "id": len(candidates) + 1,
                "name": row["name"],
                "office": office,
                "district": parse_district(office),
                "state": clean(state["name"]),
                "state_slug": state["slug"],
                "region": row.get("region", ""),
                "state_wfp_page": state["wfp_url"],
                "source_url": PAGE_URL,
            })
    return candidates


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = scrape()

    fields = list(candidates[0].keys())
    with open(out_dir / "candidates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)

    payload = {
        "source": PAGE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(candidates),
        "candidates": candidates,
    }
    with open(out_dir / "candidates.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    states = len({c["state"] for c in candidates})
    print(f"Wrote {len(candidates)} candidates across {states} states to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
