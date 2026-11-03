"""Clarity ENR sources: Colorado (with its county sub-elections), South Carolina, Florida's mirror, and the county
sites that carry WFP county races in Texas, New Jersey and Ohio. Each is just configuration.

County sites report only their county's share of state and federal contests, so those are marked `partial` and
the matcher ignores them; their county races and measures are complete.
"""
from ..platforms.clarity import ClaritySource


def county(id, state, name, site=None):
    return ClaritySource(id, state, f"{name} County (Clarity)", site or f"{state}/{name.replace(' ', '_')}",
                         tiers=(4,), level="county", county=name)


SOURCES = [
    # Colorado's county sub-elections, for the counties with WFP county races or local measures.
    ClaritySource("co", "CO", "Colorado SoS results", "CO", counties=[
        "Adams", "Arapahoe", "Boulder", "Denver", "Douglas", "El Paso", "Garfield", "Jefferson", "Larimer",
        "Pueblo", "Saguache", "Weld"]),
    ClaritySource("sc", "SC", "South Carolina Election Commission results", "SC", tiers=(1, 2)),
    ClaritySource("fl", "FL", "Florida Division of Elections (Clarity mirror)", "FL", tiers=(1,)),
    county("tx.bexar", "TX", "Bexar"),
    county("tx.dallas", "TX", "Dallas"),
    county("tx.denton", "TX", "Denton"),
    county("tx.tarrant", "TX", "Tarrant"),
    county("tx.travis", "TX", "Travis"),
    county("nj.hudson", "NJ", "Hudson"),
    county("nj.middlesex", "NJ", "Middlesex"),
    county("oh.hamilton", "OH", "Hamilton"),
]
