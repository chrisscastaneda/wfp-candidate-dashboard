"""Where source results live on disk. Only this module knows the latest/ and history/ layout.

latest/<source>.json always holds the newest good contests plus the newest status. A blocked or failed pull updates
the status but keeps the previous contests. history/<source>/<run_id>.json is written only when the contests change
(compared by content hash), so a night of polling doesn't pile up identical files.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import config
from .model import OK, Contest, SourceResult

LATEST = config.RESULTS_DIR / "latest"
HISTORY = config.RESULTS_DIR / "history"


def write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def _hash(contests: list[dict]) -> str:
    # Feed timestamps are left out: some feeds stamp every response with the current time (Nebraska's CSV), and
    # only a change in votes, choices or reporting should count as new results.
    stable = [{k: v for k, v in c.items() if k != "feed_updated_at"} for c in contests]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:16]


def load(source_id: str) -> dict | None:
    path = LATEST / f"{source_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def decode(record: dict) -> dict:
    """The record with its contests as Contest objects."""
    return {**record, "contests": [Contest.from_dict(c) for c in record.get("contests", [])]}


def load_all() -> dict[str, dict]:
    """Every source's latest record: {source_id: {status, fetched_at, contests: [Contest], ...}}."""
    paths = sorted(LATEST.glob("*.json")) if LATEST.exists() else []
    return {p.stem: decode(json.loads(p.read_text(encoding="utf-8"))) for p in paths}


def merge(previous: dict | None, result: SourceResult) -> tuple[dict, bool]:
    """The new latest record for a pull, and whether its contests changed. Pure, so --dry-run can use it."""
    record = dict(previous or {"source": result.source, "contests": [], "contests_hash": None})
    record.update(status=result.status, message=result.message, last_attempt_at=result.fetched_at)
    changed = False
    if result.status == OK:
        contests = [c.to_dict() for c in result.contests]
        digest = _hash(contests)
        changed = digest != record.get("contests_hash")
        record["fetched_at"] = result.fetched_at
        if changed:
            record.update(contests=contests, contests_hash=digest, contests_changed_at=result.fetched_at)
    return record, changed


def save(source_id: str, record: dict, changed: bool, run_id: str) -> None:
    """Write a record from merge() as the source's latest, plus a history snapshot if its contests changed."""
    write_json_atomic(LATEST / f"{source_id}.json", record)
    if changed:
        write_json_atomic(HISTORY / source_id / f"{run_id}.json", record)
