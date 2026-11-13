"""Compare two copies of data/results/wfp_results.json and print what changed, for the scraper notes.

  .venv/bin/python .claude/skills/update-results/compare.py BEFORE.json [AFTER.json]

AFTER defaults to data/results/wfp_results.json. Seats per contest come from data/results/latest/<source>.json (the
published file doesn't carry them), so multi-seat margins are measured against the last winning or first losing seat.
Margins are WFP's votes minus the rival across the winning line: positive means leading.
"""
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "data" / "results"
COUNTED = ("counting", "final")


def load(path):
    return json.loads(Path(path).read_text())


def seats_by_contest():
    """(source, contest title) -> seats, from the stored source results."""
    out = {}
    for f in (RESULTS / "latest").glob("*.json"):
        for c in load(f).get("contests") or []:
            out[(f.stem, c.get("title"))] = c.get("vote_for") or 1
    return out


def margin(result, seats):
    choices = result.get("choices") or []
    wfp = next((c for c in choices if c.get("is_wfp")), None)
    if not wfp or result.get("uncontested"):
        return None
    others = sorted((c["votes"] for c in choices if not c.get("is_wfp")), reverse=True)
    if len(others) < seats:
        return None  # fewer rivals than seats: nothing to beat
    return wfp["votes"] - others[seats - 1]


def total_votes(result):
    return sum(c["votes"] for c in result.get("choices") or []) or 1


def main():
    before = load(sys.argv[1])
    after = load(sys.argv[2] if len(sys.argv) > 2 else RESULTS / "wfp_results.json")
    candidates = {str(c["id"]): c for c in load(REPO / "data" / "candidates.json")["candidates"]}
    seats = seats_by_contest()
    a, b = before["results"], after["results"]

    def label(k):
        c = candidates.get(k, {})
        return f"{c.get('name', k)} ({c.get('state', '?')}; {b[k].get('contest') or c.get('office', '')})"

    def counts(results):
        st = collections.Counter(v["status"] for v in results.values())
        leading = sum(1 for v in results.values() if v["status"] in COUNTED and v.get("wfp_leading"))
        return st, st["counting"] + st["final"], leading

    (st_a, n_a, lead_a), (st_b, n_b, lead_b) = counts(a), counts(b)
    print(f"Races with results: {n_a:,} -> {n_b:,}; WFP leading: {lead_a:,} -> {lead_b:,}")
    print("Statuses now: " + ", ".join(f"{k} {v}" for k, v in sorted(st_b.items())))

    print("\nSources:")
    for sid, info in sorted(after.get("sources", {}).items()):
        old = before.get("sources", {}).get(sid, {}).get("status")
        if info["status"] not in ("ok", "not_modified", "derived") or old != info["status"]:
            message = (info.get("message") or "").strip().splitlines()
            print(f"  {sid}: {old} -> {info['status']}" + (f" ({message[0]})" if message else ""))

    changed = collections.Counter()
    status_changes, flips, closing, widening, new = [], [], [], [], []
    for k, v in b.items():
        o = a.get(k)
        if o is None:
            new.append(label(k))
            continue
        if v["status"] != o["status"]:
            status_changes.append(f"{label(k)}: {o['status']} -> {v['status']}")
        wv = next((c for c in v.get("choices") or [] if c.get("is_wfp")), None)
        wo = next((c for c in o.get("choices") or [] if c.get("is_wfp")), None)
        if wv and wo and wv["votes"] != wo["votes"]:
            changed[v.get("source")] += 1
        if v["status"] not in COUNTED or o["status"] not in COUNTED:
            continue
        n = seats.get((v.get("source"), v.get("contest")), 1)
        m_new, m_old = margin(v, n), margin(o, n)
        if m_new is None or m_old is None:
            continue
        seat_note = f", {n} seats" if n > 1 else ""
        line = f"{label(k)}: {m_old:+,} -> {m_new:+,}{seat_note}"
        if (m_old > 0) != (m_new > 0) or bool(o.get("wfp_leading")) != bool(v.get("wfp_leading")):
            flips.append(line + (" (now leading)" if v.get("wfp_leading") else " (now trailing)"))
        elif m_new != m_old and abs(m_new) / total_votes(v) < 0.05:
            (closing if abs(m_new) < abs(m_old) else widening).append((abs(m_new), line))

    print(f"\nVote counts changed in {sum(changed.values())} races: "
          + ", ".join(f"{s} {n}" for s, n in changed.most_common()))
    for title, items in (("Status changes", status_changes), ("New races", new), ("Flipped", flips)):
        print(f"\n{title} ({len(items)}):")
        for item in items:
            print("  " + item)
    for title, items in (("Closing (within 5%)", closing), ("Widening (within 5%)", widening)):
        print(f"\n{title} ({len(items)}):")
        for _, item in sorted(items)[:25]:
            print("  " + item)
    hand_entries()


def hand_entries():
    """Hand-entered contests with votes, oldest first, flagging the ones whose note asks for a re-entry."""
    import csv
    entered = {}
    with open(RESULTS / "manual_entries.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not (row.get("votes") or "").strip():
                continue  # template rows waiting for a count
            entered.setdefault(row["contest_id"], row)
    print(f"\nHand entries ({len(entered)}; only change when re-entered):")
    for cid, row in sorted(entered.items(), key=lambda kv: kv[1].get("as_of") or ""):
        note = row.get("note") or ""
        due = " [re-entry noted]" if "re-enter" in note.lower() else ""
        print(f"  {cid}: as of {row.get('as_of') or 'not dated'}{due}")


if __name__ == "__main__":
    main()
