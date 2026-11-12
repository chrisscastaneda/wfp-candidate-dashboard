"""Clarity ENR sources: Colorado (with its county sub-elections) and the county
sites that carry WFP county races in Texas, New Jersey and Ohio. Each is just configuration.

County sites report only their county's share of state and federal contests, so those are marked `partial` and
the matcher ignores them; their county races and measures are complete.
"""
from ..platforms.clarity import ClaritySource


def county(id, state, name, site=None, eid=None):
    return ClaritySource(id, state, f"{name} County (Clarity)", f"{name} County",
                         site or f"{state}/{name.replace(' ', '_')}", tiers=(4,), level="county", county=name, eid=eid)


SOURCES = [
    # Colorado's county sub-elections, for the counties with WFP county races or local measures.
    ClaritySource("co", "CO", "Colorado SoS results", "Colorado Secretary of State", "CO", counties=[
        "Adams", "Arapahoe", "Boulder", "Denver", "Douglas", "El Paso", "Garfield", "Jefferson", "Larimer",
        "Pueblo", "Saguache", "Weld"]),
    county("tx.bexar", "TX", "Bexar", eid="127291"),  # Nov 3 id linked from elections.bexar.org; not in elections.json
    county("tx.dallas", "TX", "Dallas", eid="127396"),  # Nov 3 id linked from dallascountyvotes.org; not in elections.json
    county("tx.denton", "TX", "Denton"),
    county("tx.tarrant", "TX", "Tarrant", eid="127297"),  # Nov 3 id linked from tarrantcountytx.gov; not in elections.json
    county("tx.travis", "TX", "Travis"),
    county("nj.hudson", "NJ", "Hudson", eid="127495"),  # Nov 3 id from hudsoncountyclerk.org; not in elections.json
    county("nj.middlesex", "NJ", "Middlesex"),
    county("oh.hamilton", "OH", "Hamilton"),
]
