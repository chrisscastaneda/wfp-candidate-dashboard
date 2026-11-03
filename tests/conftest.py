"""Shared test helpers. Tests run offline against feed responses saved in tests/fixtures/ (the real Nov 3
contest lists, captured with zero votes on Nov 2)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scrapers"))

from elex.fetch import NotFound  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class FakeFetch:
    """Stands in for SourceFetcher: maps URL fragments (plus params) to fixture files."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.requests = []

    def post(self, url, data, *, params=None, expect="text"):
        return self.get(url, params={**(params or {}), **{k: v for k, v in data.items() if not k.startswith("__")}},
                        expect=expect)

    def get(self, url, *, params=None, expect="json"):
        key = url + ("?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items())) if params else "")
        self.requests.append(key)
        for fragment, target in self.routes.items():
            if fragment in key:
                if isinstance(target, Exception):
                    raise target
                text = (FIXTURES / target).read_text(encoding="utf-8-sig")
                if expect == "text":
                    return text
                return json.loads(text)
        raise NotFound(key)

