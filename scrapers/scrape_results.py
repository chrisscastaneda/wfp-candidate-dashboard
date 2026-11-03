#!/usr/bin/env python3
"""Election results driver: pull official results feeds, match them to WFP endorsements, and write the
dashboard's data/results/wfp_results.json. Every run is logged to logs/results/.

Usage (from the repo root, with the virtualenv from requirements.txt):
    .venv/bin/python scrapers/scrape_results.py [run] [--states CA,PA] [--level state|county|all]
                                                [--counties "CA:Los Angeles"] [--sources ca,nc]
                                                [--watch MINUTES] [--dry-run] [--no-publish] [-v]
    .venv/bin/python scrapers/scrape_results.py list [--states …] [--level …]
    .venv/bin/python scrapers/scrape_results.py match
    .venv/bin/python scrapers/scrape_results.py manual-template [--force]

Exit codes: 0 if every selected source was healthy, 1 if any was blocked or failed, 2 for bad arguments.
See docs/election-results-scraper-plan.md for the design.
"""
import argparse
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from elex import config, registry, store  # noqa: E402
from elex.fetch import Fetcher  # noqa: E402
from elex.run import match_and_publish, run  # noqa: E402
from elex.runlog import RunLog  # noqa: E402
from elex.states import manual  # noqa: E402

COMMANDS = ("run", "list", "match", "manual-template")


def _csv_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_args(argv: list[str]) -> argparse.Namespace:
    if not argv or argv[0] not in COMMANDS + ("-h", "--help"):
        argv = ["run", *argv]
    parser = argparse.ArgumentParser(prog="scrape_results.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add_selection(p):
        p.add_argument("--states", type=_csv_list, help="two-letter codes, comma-separated (default: all)")
        p.add_argument("--level", choices=("state", "county", "all"), default="all")
        p.add_argument("--counties", type=_csv_list, help='county sources, e.g. "CA:Los Angeles,NY:Erie"')
        p.add_argument("--sources", type=_csv_list, help="exact source ids, e.g. ca,nc")

    p = sub.add_parser("run", help="pull, store, match, publish, log (the default)")
    add_selection(p)
    p.add_argument("--watch", type=float, metavar="MINUTES", help="repeat every N minutes until Ctrl-C")
    p.add_argument("--dry-run", action="store_true", help="fetch, parse and match, but write nothing to data/")
    p.add_argument("--no-publish", action="store_true", help="leave wfp_results.json alone")
    p.add_argument("-v", "--verbose", action="store_true", help="echo the full log")

    p = sub.add_parser("list", help="show registered sources and their last status (no network)")
    add_selection(p)
    sub.add_parser("match", help="re-run matching and publishing from stored results (no network)")
    p = sub.add_parser("manual-template", help="create or extend data/results/manual_entries.csv")
    p.add_argument("--force", action="store_true", help="start the file over, discarding entered votes")
    return parser.parse_args(argv)


def _select(args):
    return registry.select(states=args.states, level=args.level, counties=args.counties, ids=args.sources)


def cmd_list(args) -> int:
    print(f"{'source':<8} {'state':<5} {'level':<6} {'tiers':<8} {'platform':<28} {'last status':<14} last pull")
    for s in _select(args):
        record = store.load(s.id) or {}
        tiers = ",".join(str(t) for t in sorted(s.tiers))
        print(f"{s.id:<8} {s.state or '-':<5} {s.level:<6} {tiers:<8} {s.platform:<28} "
              f"{record.get('status', 'never run'):<14} {record.get('last_attempt_at') or ''}")
    return 0


def cmd_match(args) -> int:
    with RunLog("results", command="match") as log:
        log.summary["matching"] = match_and_publish(store.load_all(), log, write=True, do_publish=True)
    return 0


def cmd_manual_template(args) -> int:
    # Federal races in states whose scraper is missing, blocked or not yet publishing are entered by hand.
    working = {s.state for s in registry.ALL if s.state and (store.load(s.id) or {}).get("status") == "ok"}
    untested = registry.covered_states() - working - {s.state for s in registry.ALL if store.load(s.id)}
    covered = working | untested
    added, ids = manual.write_template(covered, force=args.force)
    print(f"{config.MANUAL_FILE.relative_to(config.REPO)}: added {added} races" + (f": {', '.join(ids)}" if ids
                                                                                    else ""))
    if untested:
        print(f"Not yet run, so assumed covered: {', '.join(sorted(untested))}. Run the scrapers first to include "
              f"any that turn out blocked.")
    return 0


def cmd_run(args) -> int:
    sources = _select(args)
    command = "run " + shlex.join(sys.argv[1:] if sys.argv[1:2] != ["run"] else sys.argv[2:])
    fetcher = Fetcher()
    kwargs = dict(command=command.strip(), dry_run=args.dry_run, do_publish=not args.no_publish,
                  verbose=args.verbose)
    if not args.watch:
        return run(sources, fetcher, **kwargs)
    code = 0
    try:
        while True:
            started = time.monotonic()
            code = run(sources, fetcher, **kwargs)
            pause = max(0.0, args.watch * 60 - (time.monotonic() - started))
            next_at = datetime.now(timezone.utc).timestamp() + pause
            print(f"next run at {datetime.fromtimestamp(next_at).strftime('%H:%M:%S')} (Ctrl-C to stop)\n",
                  flush=True)
            time.sleep(pause)
    except KeyboardInterrupt:
        print("\nstopped")
    return code


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    try:
        return {"run": cmd_run, "list": cmd_list, "match": cmd_match,
                "manual-template": cmd_manual_template}[args.command](args)
    except registry.SelectionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
