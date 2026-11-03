"""Election-wide settings and the repository paths every other module uses.

Only elex.store, elex.match, elex.publish and elex.runlog should need the paths; sources only need the date.
"""
from datetime import date
from pathlib import Path

ELECTION_DATE = date(2026, 11, 3)

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data"
CANDIDATES_FILE = DATA_DIR / "candidates.json"
RESULTS_DIR = DATA_DIR / "results"
MATCHES_FILE = RESULTS_DIR / "matches.csv"
MANUAL_FILE = RESULTS_DIR / "manual_entries.csv"
PUBLISH_FILE = RESULTS_DIR / "wfp_results.json"
SOURCES_CSV = REPO / "docs" / "results_sources.csv"
LOG_DIR = REPO / "logs"

# Seconds between requests to one host (default 1). Ohio's API needs one request per contest, so it gets less.
HOST_GAPS = {"liveresults.ohiosos.gov": 0.25}

USER_AGENT = "wfp-results-scraper/0.1 (+https://github.com/; election results for WFP endorsements)"

STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
    "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
