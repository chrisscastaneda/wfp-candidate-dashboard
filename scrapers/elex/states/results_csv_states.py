"""New Mexico and Nebraska: same results vendor, CSV exports, so each is just configuration.

New Mexico's STATE group already includes its county races (the CTY group), so SW + STATE covers everything.
Nebraska's state site has no county offices, so WFP's three Nebraska endorsements (Douglas and Lancaster County
races) won't match from it; they need county sources or manual entries.
"""
from ..platforms.results_csv import ResultsCsvSource

SOURCES = [
    ResultsCsvSource("nm", "NM", "New Mexico SoS results", "New Mexico Secretary of State",
                     "https://electionresults.sos.nm.gov", ["SW", "STATE"]),
    ResultsCsvSource("ne", "NE", "Nebraska SoS results", "Nebraska Secretary of State",
                     "https://electionresults.nebraska.gov", ["All"], tiers=(4,),
                     local_races=False),
]
