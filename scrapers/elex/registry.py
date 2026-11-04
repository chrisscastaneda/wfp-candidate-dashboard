"""Every results source, and selection by state, level, county or id. Adding a scraper means adding its module's
SOURCES here.
"""
from .counties import ca as ca_counties
from .counties import ny as ny_counties
from .source import Source
from .states import ca, clarity_states, ct, de, enhanced_voting_states, manual, md, nc, oh, or_, pa, results_csv_states

ALL: list[Source] = [
    *ca.SOURCES, *pa.SOURCES, *nc.SOURCES, *enhanced_voting_states.SOURCES, *results_csv_states.SOURCES,
    *clarity_states.SOURCES, *ct.SOURCES, *or_.SOURCES, *oh.SOURCES, *de.SOURCES, *md.SOURCES,
    *ca_counties.SOURCES, *ny_counties.SOURCES,
    *manual.SOURCES,
]


class SelectionError(ValueError):
    pass


def select(states=None, level="all", counties=None, ids=None) -> list[Source]:
    """Sources matching every filter given. `counties` is ["CA:Los Angeles", ...] and implies level "county".
    The manual source has no state and is included unless `ids` names sources without it."""
    by_id = {s.id: s for s in ALL}
    if ids:
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            raise SelectionError(f"unknown source id(s): {', '.join(unknown)}. Try the list command.")
        return [by_id[i] for i in ids]
    chosen = ALL
    if counties:
        wanted = {(c.split(":")[0].strip().upper(), c.split(":", 1)[1].strip().lower()) for c in counties if ":" in c}
        chosen = [s for s in chosen if s.level == "county" and (s.state, (s.county or "").lower()) in wanted]
        if not chosen:
            raise SelectionError(f"no county sources for {', '.join(counties)} yet (county scrapers are Phase 3)")
        return chosen
    if level != "all":
        chosen = [s for s in chosen if s.level == level or not s.state]
    if states:
        wanted_states = {s.upper() for s in states}
        chosen = [s for s in chosen if s.state in wanted_states or not s.state]
    return chosen

