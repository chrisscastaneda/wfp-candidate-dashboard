"""Georgia, Utah, Washington and Rhode Island: Enhanced Voting sites, so each is just configuration.

Georgia and Washington returned 403 on Nov 2 (WA: "final launch preparations"). They report `blocked` until the
sites open, then work with no code changes. Their locality names are resolved against the site's own county list
at run time; a name that doesn't match is skipped, and its races show up as unmatched in matches.csv.
"""
from ..platforms.enhanced_voting import EnhancedVotingSource

SOURCES = [
    EnhancedVotingSource("ga", "GA", "Georgia SoS results", "https://results.sos.ga.gov", "Georgia",
                         localities=["DeKalb County", "Fulton County"]),
    # Utah's single-county legislative districts are only on county sub-sites: HD 21/32/35 and the Salt Lake
    # County races are on Salt Lake County's; HD 62 is on Utah County's.
    EnhancedVotingSource("ut", "UT", "Utah election results", "https://electionresults.utah.gov", "Utah",
                         localities=["Salt Lake County", "Utah County"], tiers=(2, 4)),
    EnhancedVotingSource("wa", "WA", "Washington SoS results", "https://results.votewa.gov", "washington",
                         localities=["King County", "Spokane County"]),
    # Rhode Island's state file already includes city and town races (Providence, East Providence).
    EnhancedVotingSource("ri", "RI", "Rhode Island Board of Elections results", "https://electionresults.ri.gov",
                         "rhodeisland", tiers=(2, 4)),
]
