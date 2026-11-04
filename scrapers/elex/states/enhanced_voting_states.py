"""Georgia, Utah, Washington, Rhode Island and Arizona: Enhanced Voting sites, so each is just configuration.

Georgia and Washington returned 403 on Nov 2 (WA: "final launch preparations"). They report `blocked` until the
sites open, then work with no code changes. Their locality names are resolved against the site's own county list
at run time; a name that doesn't match is skipped, and its races show up as unmatched in matches.csv.
"""
from ..platforms.enhanced_voting import EnhancedVotingSource

SOURCES = [
    EnhancedVotingSource("ga", "GA", "Georgia SoS results", "Georgia Secretary of State",
                         "https://results.sos.ga.gov", "Georgia",
                         localities=["DeKalb County", "Fulton County"]),
    # Utah's single-county legislative districts are only on county sub-sites: HD 21/32/35 and the Salt Lake
    # County races are on Salt Lake County's; HD 62 is on Utah County's.
    EnhancedVotingSource("ut", "UT", "Utah election results", "Utah Lieutenant Governor",
                         "https://electionresults.utah.gov", "Utah",
                         localities=["Salt Lake County", "Utah County"], tiers=(2, 4)),
    EnhancedVotingSource("wa", "WA", "Washington SoS results", "Washington Secretary of State",
                         "https://results.votewa.gov", "washington",
                         localities=["King County", "Spokane County"]),
    # Rhode Island's state file already includes city and town races (Providence, East Providence).
    EnhancedVotingSource("ri", "RI", "Rhode Island Board of Elections results",
                         "Rhode Island Board of Elections", "https://electionresults.ri.gov",
                         "rhodeisland", tiers=(2, 4), units=("city or town", "cities and towns")),
    # results.arizona.vote is behind a Cloudflare challenge, but its Nov 3 link goes to Enhanced Voting's shared
    # host, which scripts can read. County files there (Maricopa) repeat the state's races and have no city races;
    # Phoenix runs its own council elections.
    EnhancedVotingSource("az", "AZ", "Arizona SoS results (Enhanced Voting)", "Arizona Secretary of State",
                         "https://app.enhancedvoting.com", "Arizona"),
]
