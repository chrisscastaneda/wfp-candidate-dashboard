"""A log for every data pull: logs/<kind>/<run_id>.log (readable) and <run_id>.json (summary).

Standard library only, so the candidate scraper can use it too:

    with RunLog("candidates", command="scrape_wfp_candidates.py") as log:
        log.info("Fetched 1,216 rows")
        log.summary["count"] = 1216

The run_id is the UTC start time, e.g. 20261103T031502Z. An exception inside the block is logged with its traceback
and recorded in the summary before it propagates.
"""
import json
import sys
import traceback
from datetime import datetime, timezone

from . import config


class RunLog:
    def __init__(self, kind: str, command: str = "", echo: bool = False):
        self.started = datetime.now(timezone.utc)
        self.run_id = self.started.strftime("%Y%m%dT%H%M%SZ")
        self.dir = config.LOG_DIR / kind
        self.echo = echo
        self.summary: dict = {"run_id": self.run_id, "command": command, "started_at": self.started.isoformat(
            timespec="seconds"), "errors": []}
        self._lines: list[str] = []

    def info(self, message: str, *, echo: bool | None = None) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._lines.append(f"{stamp} {message}")
        if self.echo if echo is None else echo:
            print(message, flush=True)

    def error(self, message: str) -> None:
        self.summary["errors"].append(message)
        self.info(f"ERROR {message}", echo=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type and exc_type is not KeyboardInterrupt:
            self.error(f"{exc_type.__name__}: {exc}")
            self.info("".join(traceback.format_exception(exc_type, exc, tb)), echo=False)
        self.write()
        return False

    def write(self) -> None:
        ended = datetime.now(timezone.utc)
        self.summary["duration_s"] = round((ended - self.started).total_seconds(), 1)
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            (self.dir / f"{self.run_id}.log").write_text("\n".join(self._lines) + "\n", encoding="utf-8")
            (self.dir / f"{self.run_id}.json").write_text(json.dumps(self.summary, indent=1) + "\n", encoding="utf-8")
        except OSError as e:  # a full disk shouldn't hide the run's own outcome
            print(f"Couldn't write the run log: {e}", file=sys.stderr)
