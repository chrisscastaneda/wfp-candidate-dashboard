"""Delaware Department of Elections ENR (elections.delaware.gov/results/enr). The results page fetches JSON:

  /results/enr/Election_StatewideResults_ID_<ElectionId>.json   one row per contest and candidate, every contest
                                                                (federal, state, and county offices)

The election id is the page name ("GE2026" for GE2026.html).
"""
from collections import OrderedDict

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

URL = "https://elections.delaware.gov/results/enr/Election_StatewideResults_ID_{eid}.json"


def parse(rows: list[dict]) -> list[Contest]:
    contests: dict[str, Contest] = OrderedDict()
    for row in rows:
        title = row["Contest Title"].strip()
        contest = contests.get(title)
        if contest is None:
            contest = contests[title] = Contest(
                source="de", contest_id=title, state="DE", title=title, office_type=names.office_type(title),
                district=names.district(title), jurisdiction="Delaware", final="UNOFFICIAL" not in (
                    row.get("Results Type") or "UNOFFICIAL").upper(),
                reporting=Reporting(row.get("Precincts Reported"), row.get("Total Precincts")),
                feed_updated_at=row.get("ReportTime"))
        contest.choices.append(Choice(row["Candidate Name"], names.to_int(row.get("Total Votes")),
                                      names.party(row.get("Party Name")), choice_id=str(row.get("Candidate Id"))))
    for contest in contests.values():
        contest.fill_percentages()
    return list(contests.values())


class Delaware(Source):
    id = "de"
    state = "DE"
    title = "Delaware Department of Elections ENR"
    platform = "DE ENR JSON"
    tiers = frozenset({1, 2, 4})

    def pull(self, fetch):
        rows = fetch.get(URL.format(eid=f"GE{config.ELECTION_DATE.year}"))
        if not rows or rows[0].get("Election Date") != config.ELECTION_DATE.isoformat():
            raise NotPublished("statewide results file isn't for this election")
        return parse(rows)


SOURCES = [Delaware()]
