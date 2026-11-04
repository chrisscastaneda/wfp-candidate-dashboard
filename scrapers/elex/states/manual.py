"""Hand-entered results from data/results/manual_entries.csv, for races no scraper covers (see "Manual federal
races" in docs/election-results-scraper-plan.md).

One row per candidate. Rows sharing a contest_id form one contest. A contest whose rows all have blank votes
hasn't been entered yet and is skipped. The matcher only uses manual contests for endorsements no scraped source
matched, so a race moves off the manual list on its own once a scraper covers it.

write_template() creates or extends the file with one row per uncovered federal endorsement.
"""
import csv
from collections import OrderedDict

from .. import config, endorsements, names
from ..model import Choice, Contest, Reporting
from ..source import Source

COLUMNS = ["contest_id", "state", "office", "district", "choice", "party", "votes", "reporting_pct", "source_url",
           "as_of", "note"]


def read_rows() -> list[dict]:
    if not config.MANUAL_FILE.exists():
        return []
    with config.MANUAL_FILE.open(encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("contest_id") or "").strip()]


def parse(rows: list[dict]) -> list[Contest]:
    groups: dict[str, list[dict]] = OrderedDict()
    for row in rows:
        groups.setdefault(row["contest_id"].strip(), []).append(row)
    contests = []
    for contest_id, members in groups.items():
        entered = [r for r in members if (r.get("votes") or "").strip()]
        if not entered:
            continue
        first = members[0]
        office = first["office"].strip()
        title = f"{office} District {first['district']}" if (first.get("district") or "").strip() else office
        pct = names.to_float(first.get("reporting_pct"))
        contest = Contest(
            source="manual", contest_id=contest_id, state=first["state"].strip().upper(), title=title,
            office_type=names.office_type(office), district=(first.get("district") or "").strip() or None,
            jurisdiction=first["state"].strip().upper(),
            reporting=Reporting(pct=pct, text=f"{pct:g}% reporting" if pct is not None else None),
            feed_updated_at=(first.get("as_of") or "").strip() or None,
            url=(first.get("source_url") or "").strip() or None,
            choices=[Choice(r["choice"].strip(), names.to_int(r.get("votes")), names.party(r.get("party")))
                     for r in entered])
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Manual(Source):
    id = "manual"
    state = ""
    title = "Hand-entered results (data/results/manual_entries.csv)"
    platform = "manual CSV"
    tiers = frozenset({1, 2, 3, 4})

    def pull(self, fetch):
        return parse(read_rows())


SOURCES = [Manual()]


def _contest_id(row: dict) -> str:
    kind = "us-senate" if row["office_category"] == "Federal Senate" else "us-house"
    district = names.district(row["office"]) if kind == "us-house" else None
    return f"{row['state_code'].lower()}.{kind}" + (f".{district}" if district else "")


def write_template(covered_states: set[str], force: bool = False) -> tuple[int, list[str]]:
    """Add a row for the WFP candidate in every federal race outside `covered_states`. Existing rows are kept, so
    running it again only adds new races; `force` starts the file over. Returns (rows added, contest ids added)."""
    existing = [] if force else read_rows()
    have = {r["contest_id"] for r in existing}
    added = []
    for row in endorsements.load():
        if row["office_category"] not in ("Federal House", "Federal Senate") or row["nov3_ballot"] == "no":
            continue
        if row["state_code"] in covered_states:
            continue
        contest_id = _contest_id(row)
        if contest_id in have:
            continue
        have.add(contest_id)
        is_house = row["office_category"] == "Federal House"
        existing.append({
            "contest_id": contest_id, "state": row["state_code"],
            "office": "U.S. House" if is_house else "U.S. Senate",
            "district": names.district(row["office"]) if is_house else "", "choice": row["name"], "party": "",
            "votes": "", "reporting_pct": "", "source_url": row["official_source_url"], "as_of": "",
            "note": "WFP endorsed. Add a row per opponent with the same contest_id."})
        added.append(contest_id)
    config.MANUAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing.sort(key=lambda r: (r["contest_id"], r.get("note", "") == ""))
    with config.MANUAL_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing)
    return len(added), added
