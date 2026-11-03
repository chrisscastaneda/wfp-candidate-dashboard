"""WFP's endorsements as the results system sees them: data/candidates.json joined with the Nov 3 ballot status
and official source URL from docs/results_sources.csv.

Rows are identified by `key` (state code | name | office), not by `id`: ids are assigned in scrape order and
shift when WFP adds or removes candidates, while the key survives re-scrapes. `id` is still carried through for the
dashboard, which reads ids from the same candidates.json.
"""
import csv
import json

from . import config


def key_for(state: str, name: str, office: str) -> str:
    return f"{state}|{name}|{office}"


def load() -> list[dict]:
    rows = json.loads(config.CANDIDATES_FILE.read_text(encoding="utf-8"))["candidates"]
    extra = {}
    if config.SOURCES_CSV.exists():
        with config.SOURCES_CSV.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                extra[(r["state"], r["name"], r["office"])] = r
    out = []
    for row in rows:
        info = extra.get((row["state"], row["name"], row["office"]), {})
        code = config.STATE_CODES.get(row["state"], row["state"][:2].upper())
        out.append({**row, "state_code": code, "key": key_for(code, row["name"], row["office"]),
                    "nov3_ballot": info.get("nov3_ballot", "expected"), "nov3_note": info.get("nov3_note", ""),
                    "official_source_url": info.get("source_url", "")})
    return out
