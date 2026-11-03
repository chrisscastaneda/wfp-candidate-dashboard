"""The one interface every results scraper implements.

The driver knows only this: a Source has an id and some descriptive attributes, and pull() returns contests.
URLs, election-ID discovery, formats and quirks stay inside the source. A source signals the normal non-results
states by raising NotPublished (or letting the fetcher raise Blocked/NotFound); elex.run turns those into statuses.
"""
from .fetch import SourceFetcher
from .model import Contest


class NotPublished(Exception):
    """The election isn't on the site yet."""


class Source:
    id: str = ""                 # "ca", "ny.westchester", "manual"
    state: str = ""              # "CA"; "" for multi-state sources (manual)
    level: str = "state"         # "state" or "county"
    county: str | None = None    # for county sources: "Los Angeles"
    title: str = ""
    platform: str = ""           # "CA SoS API", "Enhanced Voting", ...
    tiers: frozenset = frozenset()
    min_interval: int = 0        # seconds between pulls in --watch
    local_races: bool = True     # False when the feed has no local races (the matcher then reports no_source)

    def pull(self, fetch: SourceFetcher) -> list[Contest]:
        raise NotImplementedError

    def __repr__(self):
        return f"<Source {self.id}>"
