"""Nebraska county sources. The state's results site (states/results_csv_states.py) has no county offices, and WFP's
Nebraska endorsements are all county races.

Douglas County (votedouglascounty-ne.gov/meer/) posts each count as a numbered Electionware "Summary Results Report"
PDF (26GNResults8.pdf is the eighth); the highest number is newest.

Lancaster County's election site (lancaster.ne.gov) refuses scripts (403), so its race is entered by hand.
"""
from ..platforms.summary_pdf import SummaryPdfSource

SOURCES = [
    SummaryPdfSource("ne.douglas", "NE", "Douglas", None, "https://www.votedouglascounty-ne.gov/meer/index.aspx",
                     "Douglas County Election Commission", link=r"/meer/\d{2}GNResults(\d+)\.pdf"),
]
