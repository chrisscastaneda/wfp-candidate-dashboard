"""HTTP for every source. Only this module knows about requests, gzip, retries, rate limits and conditional GETs.

Sources call `fetch.get(url, params=..., expect="json")` and get the decoded body. Three outcomes are exceptions,
because each one ends the source's pull and the run turns it into a status:

- Blocked: a 403/429 or a bot-challenge page. Never retried; we don't work around bot protection.
- NotFound: a 404, which on a results site means the election isn't published yet.
- FetchError: anything else that failed after retries.
"""
import json
import threading
import time
from urllib.parse import urlsplit

import requests

from . import config


class FetchError(Exception):
    pass


class Blocked(FetchError):
    pass


class NotFound(FetchError):
    pass


# Markers of bot-protection pages served with a 200 in place of data.
_CHALLENGE_MARKERS = ("_Incapsula_Resource", "cf-chl", "Just a moment...", "challenge-platform")


class Fetcher:
    """Shared across a run (and across runs in --watch). Call for_source() to get a SourceFetcher that records the
    source's requests for its log."""

    def __init__(self, min_gap: float = 1.0, timeout: float = 30, retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT, "Accept-Encoding": "gzip, deflate"})
        self.min_gap = min_gap
        self.timeout = timeout
        self.retries = retries
        self._host_locks: dict[str, threading.Lock] = {}
        self._host_last: dict[str, float] = {}
        self._locks_guard = threading.Lock()
        # url -> (etag, last_modified, body). Lets --watch send conditional GETs; empty on a one-shot run.
        self._cache: dict[str, tuple[str | None, str | None, bytes]] = {}

    def for_source(self, source_id: str) -> "SourceFetcher":
        return SourceFetcher(self, source_id)

    def _host_lock(self, host: str) -> threading.Lock:
        with self._locks_guard:
            return self._host_locks.setdefault(host, threading.Lock())

    def _request(self, url: str, params: dict | None, log: list) -> bytes:
        host = urlsplit(url).netloc
        with self._host_lock(host):  # one request at a time per host, min_gap apart
            for attempt in range(1, self.retries + 1):
                wait = self.min_gap - (time.monotonic() - self._host_last.get(host, 0))
                if wait > 0:
                    time.sleep(wait)
                cache_key = url + "?" + json.dumps(params, sort_keys=True) if params else url
                cached = self._cache.get(cache_key)
                headers = {}
                if cached:
                    if cached[0]:
                        headers["If-None-Match"] = cached[0]
                    if cached[1]:
                        headers["If-Modified-Since"] = cached[1]
                start = time.monotonic()
                entry = {"url": url, "params": params, "attempt": attempt}
                try:
                    resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
                except requests.RequestException as e:
                    entry.update(status=None, error=type(e).__name__, seconds=round(time.monotonic() - start, 2))
                    log.append(entry)
                    self._host_last[host] = time.monotonic()
                    if attempt == self.retries:
                        raise FetchError(f"{url}: {type(e).__name__}: {e}") from e
                    time.sleep(2 ** attempt)
                    continue
                self._host_last[host] = time.monotonic()
                entry.update(status=resp.status_code, bytes=len(resp.content),
                             seconds=round(time.monotonic() - start, 2))
                log.append(entry)
                if resp.status_code == 304 and cached:
                    entry["not_modified"] = True
                    return cached[2]
                if resp.status_code in (401, 403, 429):
                    raise Blocked(f"{url}: HTTP {resp.status_code}")
                if resp.status_code == 404:
                    raise NotFound(f"{url}: HTTP 404")
                if resp.status_code >= 500:
                    if attempt == self.retries:
                        raise FetchError(f"{url}: HTTP {resp.status_code}")
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code >= 400:
                    raise FetchError(f"{url}: HTTP {resp.status_code}")
                head = resp.content[:2000].decode("utf-8", "replace")
                if any(marker in head for marker in _CHALLENGE_MARKERS):
                    raise Blocked(f"{url}: bot-challenge page")
                etag, modified = resp.headers.get("ETag"), resp.headers.get("Last-Modified")
                if etag or modified:
                    self._cache[cache_key] = (etag, modified, resp.content)
                return resp.content
        raise FetchError(f"{url}: no response")  # not reached


class SourceFetcher:
    """What a source sees: get() plus the list of requests it made."""

    def __init__(self, fetcher: Fetcher, source_id: str):
        self._fetcher = fetcher
        self.source_id = source_id
        self.requests: list[dict] = []

    def get(self, url: str, *, params: dict | None = None, expect: str = "json"):
        """Return the body decoded as `expect`: "json", "text" or "bytes"."""
        body = self._fetcher._request(url, params, self.requests)
        if expect == "bytes":
            return body
        text = body.decode("utf-8-sig", "replace")
        if expect == "text":
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise FetchError(f"{url}: expected JSON, got {text[:120]!r}") from e
