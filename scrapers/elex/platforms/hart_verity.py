"""Hart InterCivic Verity "Cumulative Results Report" pages (Count_HtmlCumulativeReport), used by Stanislaus County CA.
The page is one SQL Server Reporting Services table. Its <meta> tags carry the election:

  <meta content="11/3/2026 12:00:00 AM" name="ElectionDate"/>
  <meta content="11/9/2026 5:35:42 PM" name="ReportGeneratedDate"/>

Flattened to rows of cells, each contest reads:

  City of Modesto Member, City Council - District 2 - Vote for ONE      <- title, then "Precincts"
  Precincts / Counted / Total / Percent / 14 / 14 / 100.00%
  Voters / Ballots / Registered / Percent / 5,069 / 14,823 / 34.20%
  Choice / Party / Vote Center | Vote By Mail | Total
  JUAN TELLES | 291 | 45.47% | 1,417 | 39.50% | 1,708 | 40.41%     <- one row per choice; the total is 2nd to last
  Cast Votes: / Undervotes: / Overvotes: / ... write-in votes:

Measures and judicial retention votes have no "Vote for" suffix. A county's statewide and district contests are
only its share, so they're marked partial.
"""
import html
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

# Offices a county reports only its share of; the state's results report them in full.
SHARE_KINDS = {"federal_senate", "federal_house", "state_senate", "state_house", "governor", "lt_governor",
               "secretary_of_state", "controller", "treasurer", "attorney_general", "insurance_commissioner",
               "superintendent", "board_of_equalization"}


def _meta(page: str, name: str) -> str | None:
    m = re.search(rf'<meta content="([^"]*)" name="{name}"', page)
    return m.group(1) if m else None


def rows(page: str) -> list[list[str]]:
    """The report's table rows as lists of non-empty cell texts."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", page)
    text = re.sub(r"(?i)</t[dh]>", "\t", text)
    text = re.sub(r"(?i)</tr>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    out = []
    for line in text.split("\n"):
        cells = [c.strip() for c in line.split("\t") if c.strip()]
        if cells:
            out.append(cells)
    return out


def parse(page: str, *, source_id: str, state: str, county: str, url: str | None = None) -> list[Contest]:
    generated = _meta(page, "ReportGeneratedDate")
    updated = (datetime.strptime(generated, "%m/%d/%Y %I:%M:%S %p").isoformat() + "-08:00") if generated else None
    lines = rows(page)
    contests = []
    for i, cells in enumerate(lines):
        if cells != ["Precincts"] or i == 0 or len(lines[i - 1]) != 1:
            continue
        heading = lines[i - 1][0]
        m = re.match(r"(.*?) - (Vote for .*)$", heading)
        title, vote_for = (m.group(1), names.vote_for(m.group(2))) if m else (heading, 1)
        title = re.sub(r"^For ", "", title)
        # Precincts counted and total follow the four header cells.
        nums = [c[0] for c in lines[i + 1:i + 8] if len(c) == 1]
        counted, total = (names.to_int(nums[3]), names.to_int(nums[4])) if len(nums) >= 5 else (None, None)
        # The choices follow the column header row ("Vote Center", "Vote By Mail", "Total").
        j = next((k for k in range(i + 1, min(i + 30, len(lines))) if len(lines[k]) > 1 and lines[k][-1] == "Total"),
                 None)
        choices = []
        for row in lines[j + 1:] if j is not None else []:
            if len(row) == 1 and row[0].endswith(":"):
                break
            if len(row) < 3:
                break
            name, votes = row[0], names.to_int(row[-2])
            if name.lower().startswith("write-in") and not votes:
                continue
            choices.append(Choice(name, votes, choice_id=name))
        is_measure = bool(re.search(r"(?i)\b(proposition \d+|measure [A-Z]{1,2})$", title))
        if is_measure:
            for c in choices:
                c.name = names.yes_no(c.name)
        kind = "measure" if is_measure else names.office_type(title)
        share = kind in SHARE_KINDS or bool(names.STATE_PROP.search(title)) \
            or bool(re.search(r"(?i)supreme court|court of appeal", title))
        contest = Contest(
            source=source_id, contest_id=heading, state=state, title=title, office_type=kind,
            district=names.measure_id(title) if is_measure else names.district(title),
            jurisdiction=f"{county} County", scope="partial" if share else "complete", vote_for=vote_for,
            reporting=Reporting(counted, total) if total else Reporting(), feed_updated_at=updated, url=url,
            choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class HartVeritySource(Source):
    platform = "Hart Verity cumulative report"
    level = "county"

    def __init__(self, id, state, county, report_url, site_name, tiers=(4,)):
        self.id, self.state, self.county, self.tiers = id, state, county, frozenset(tiers)
        self.title = f"{county} County cumulative results (Hart Verity)"
        self.url, self.site_name = report_url, site_name

    def pull(self, fetch):
        page = fetch.get(self.url, expect="text")
        when = next(iter((_meta(page, "ElectionDate") or "").split()), "")
        try:
            day = datetime.strptime(when, "%m/%d/%Y").date()
        except ValueError:
            day = None
        if day != config.ELECTION_DATE:
            raise NotPublished(f"{self.url} is for {when or 'no date'}, not {config.ELECTION_DATE}")
        return parse(page, source_id=self.id, state=self.state, county=self.county, url=self.url)
