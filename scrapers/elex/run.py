"""One run: pull the selected sources concurrently, store, match, publish, log.

Every source's outcome becomes a status, so one failing source never stops the run. The driver calls run() once,
or in a loop for --watch, sharing one Fetcher so conditional GETs work across polls.
"""
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import combine, endorsements, match, publish, registry, store
from .fetch import Blocked, Fetcher, FetchError, NotFound
from .model import BLOCKED, ERROR, HEALTHY, NOT_MODIFIED, NOT_PUBLISHED, OK, SKIPPED, SourceResult
from .runlog import RunLog
from .source import NotPublished, Source


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _due(source: Source) -> bool:
    if not source.min_interval:
        return True
    record = store.load(source.id)
    if not record or not record.get("fetched_at"):
        return True
    last = datetime.fromisoformat(record["fetched_at"])
    return (datetime.now(timezone.utc) - last).total_seconds() >= source.min_interval


def pull(source: Source, fetcher: Fetcher) -> SourceResult:
    """Run one source's pull and turn its outcome into a SourceResult. Never raises."""
    if not _due(source):
        return SourceResult(source.id, SKIPPED, message=f"min_interval {source.min_interval}s not reached")
    fetch = fetcher.for_source(source.id)
    start = time.monotonic()
    result = SourceResult(source.id, OK, fetched_at=_now())
    try:
        result.contests = source.pull(fetch)
    except Blocked as e:
        result.status, result.message = BLOCKED, str(e)
    except (NotPublished, NotFound) as e:
        result.status, result.message = NOT_PUBLISHED, str(e)
    except FetchError as e:
        result.status, result.message = ERROR, str(e)
    except Exception as e:  # a parser bug in one source must not stop the others
        result.status, result.message = ERROR, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    result.seconds = round(time.monotonic() - start, 1)
    result.requests = fetch.requests
    return result


def _describe(r: SourceResult) -> str:
    detail = {OK: f"{len(r.contests)} contests, changed", NOT_MODIFIED: f"{len(r.contests)} contests, unchanged"
              }.get(r.status, r.message.splitlines()[0] if r.message else "")
    return f"{r.source:<8} {r.status:<13} {detail}  ({len(r.requests)} requests, {r.seconds}s)"


def match_and_publish(latest: dict, log: RunLog, *, write: bool, do_publish: bool) -> dict:
    """Re-match every endorsement against `latest`, log what changed, and write the review file and the
    dashboard file. Returns the match counts."""
    rows_in = endorsements.load()
    previous = match.read_review_file()
    contests = [c for rec in latest.values() for c in rec.get("contests", [])]
    local_states = {s.state for s in registry.ALL if s.state and s.level == "state" and s.local_races}
    local_counties = {(s.state, s.county) for s in registry.ALL if s.level == "county"}
    statewide_states = {s.state for s in registry.ALL if s.state and s.level == "state"}
    rows = match.match_all(rows_in, contests, previous, local_states, statewide_states, local_counties)
    for line in match.changes(previous, rows):
        log.info(line)
    counts = match.counts(rows)
    log.info("matching: " + ", ".join(f"{k} {v}" for k, v in counts.items()), echo=True)
    if write:
        match.write_review_file(rows)
        if do_publish:
            publish.write(publish.build(rows_in, rows, latest, log.run_id))
            log.info("published data/results/wfp_results.json", echo=True)
    return counts


def _derive(latest: dict, log: RunLog, dry_run: bool) -> None:
    """Rebuild district races summed from county results (combine.py) from the latest stored county results."""
    contests, skipped = combine.build(latest, registry.ALL)
    for line in skipped:
        log.info(f"  {combine.CountySums.id} skipped {line}")
    result = SourceResult(combine.CountySums.id, OK, contests, fetched_at=_now())
    record, changed = store.merge(store.load(result.source), result)
    if not dry_run:
        store.save(result.source, record, changed, log.run_id)
    latest[result.source] = store.decode(record)
    log.info(f"{result.source:<8} derived       {len(contests)} district contests summed from county results"
             f"{', changed' if changed else ''}", echo=True)


def run(sources: list[Source], fetcher: Fetcher, *, command: str, dry_run=False, do_publish=True,
        verbose=False) -> int:
    """Pull, store, match, publish and log once. Returns the exit code: 0 if every source is healthy, else 1."""
    started = time.monotonic()
    with RunLog("results", command=command, echo=verbose) as log:
        log.info(f"run {log.run_id}: {len(sources)} sources" + (" (dry run)" if dry_run else ""), echo=True)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda s: pull(s, fetcher),
                                    [s for s in sources if not getattr(s, "derived", False)]))
        latest = store.load_all()
        log.summary["sources"] = {}
        for r in results:
            if r.status != SKIPPED:
                record, r.changed = store.merge(store.load(r.source), r)
                if not dry_run:
                    store.save(r.source, record, r.changed, log.run_id)
                latest[r.source] = store.decode(record)
            if r.status == OK and not r.changed:
                r.status = NOT_MODIFIED
            for q in r.requests:
                log.info(f"  {r.source} GET {q['url']} {q.get('params') or ''} -> {q.get('status')} "
                         f"{q.get('bytes', 0)}B {q.get('seconds')}s {q.get('error', '')}"
                         f"{' TLS NOT VERIFIED: ' + q['tls_unverified'] if q.get('tls_unverified') else ''}".rstrip())
            log.info(_describe(r), echo=True)
            if r.status in (BLOCKED, ERROR):
                log.error(f"{r.source}: {r.message}")
            log.summary["sources"][r.source] = {
                "status": r.status, "contests": len(r.contests), "changed": r.changed, "requests": len(r.requests),
                "bytes": sum(q.get("bytes", 0) for q in r.requests), "seconds": r.seconds,
                **({"message": r.message.splitlines()[0]} if r.message else {})}
        _derive(latest, log, dry_run)
        log.summary["matching"] = match_and_publish(latest, log, write=not dry_run, do_publish=do_publish)
        log.info(f"done in {time.monotonic() - started:.1f}s; log at logs/results/{log.run_id}.log", echo=True)
    return 0 if all(r.status in HEALTHY for r in results) else 1
