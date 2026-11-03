"""Builds data/results/wfp_results.json, the one file the dashboard reads, from the latest source records and the
match table. The format is the data contract in docs/election-results-scraper-plan.md. We report votes and
`wfp_leading`; we don't call races.
"""
from datetime import datetime, timezone

from . import config, match
from .model import Contest
from .store import write_json_atomic

# Endorsement statuses
AWAITING, COUNTING, FINAL = "awaiting", "counting", "final"


def _leading(contest: Contest, wfp_choice_id: str) -> bool | None:
    """Whether WFP's choice is currently in a winning position (top `vote_for`). None before any votes."""
    if not contest.total_votes:
        return None
    ranked = sorted(contest.choices, key=lambda c: c.votes, reverse=True)
    cutoff = ranked[min(contest.vote_for, len(ranked)) - 1].votes
    wfp = next((c for c in contest.choices if c.choice_id == wfp_choice_id), None)
    return bool(wfp and wfp.votes >= cutoff and wfp.votes > 0)


def build(endorsements: list[dict], match_rows: list[dict], latest: dict[str, dict], run_id: str) -> dict:
    by_key = {f"{r['state']}|{r['name']}|{r['office']}": r for r in match_rows}
    contests = {(sid, c.contest_id): c for sid, rec in latest.items() for c in rec.get("contests", [])}
    results = {}
    for e in endorsements:
        m = by_key.get(e["key"])
        status = m["status"] if m else match.NO_SOURCE
        # The name lets the dashboard spot a results file built from an older candidates.json (ids shift).
        entry = {"name": e["name"], "status": status, "match_status": status}
        contest = contests.get((m["source"], m["contest_id"])) if m and m["contest_id"] else None
        if status in (match.NOT_ON_BALLOT, match.NO_SOURCE, match.UNMATCHED) or contest is None:
            if status not in (match.NOT_ON_BALLOT, match.NO_SOURCE):
                entry["status"] = match.UNMATCHED
            if m and m.get("note"):
                entry["note"] = m["note"]
            results[str(e["id"])] = entry
            continue
        entry.update(
            status=FINAL if contest.final else COUNTING if contest.total_votes else AWAITING,
            source=contest.source, contest=contest.title, scope=contest.scope,
            reporting={"pct": contest.reporting.pct, "text": contest.reporting.text},
            updated_at=contest.feed_updated_at or latest[contest.source].get("fetched_at"),
            wfp_choice=m["choice"], wfp_leading=_leading(contest, m["choice_id"]),
            choices=[{"name": c.name, "party": c.party, "votes": c.votes, "pct": c.pct,
                      "is_wfp": c.choice_id == m["choice_id"]}
                     for c in sorted(contest.choices, key=lambda c: c.votes, reverse=True)])
        results[str(e["id"])] = entry
    return {
        "election_date": config.ELECTION_DATE.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "sources": {sid: {"status": rec.get("status"), "fetched_at": rec.get("fetched_at"),
                          "contests_changed_at": rec.get("contests_changed_at"), "message": rec.get("message") or None}
                    for sid, rec in sorted(latest.items())},
        "results": results,
    }


def write(payload: dict) -> None:
    write_json_atomic(config.PUBLISH_FILE, payload)
