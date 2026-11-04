"""Michigan county sources. The Secretary of State posts statewide unofficial results about a day after the
election, so election night means county sites: Wayne (TotalVote) and Washtenaw (its own results pages). Bay County
posts PDFs, so its two races are entered by hand.

Wayne County's own site (waynecountymi.gov) returns 403 to scripts, but its results page links to TotalVote
(michigan.totalvote.com/Wayne), which doesn't. One server-rendered page per contest category:

  /Wayne/ResultsSW.aspx?type=<CON|SEN|REP|...>&cid=05
    each contest: <h1>Title - <br>VOTE FOR ONE (1)</h1>, "Precincts Reported: n / m", then per candidate
    <div class="... display-results-box-d"><h1>Name</h1><h2 class="DEM">Democratic</h2> ...
    <div class="... display-results-box-f"><h1>9,015</h1>
  "Results Last Updated: 11/3/2026 11:06:34 PM EST" near the top

Only districts entirely inside Wayne County are complete (`whole_districts`): MI-13, SD-2, HD-26 and HD-27, per the
district lists on Wikipedia. MI-13 also takes in a sliver of Grosse Pointe Shores that's in Macomb County; that's
a handful of votes, so it's treated as complete. MI-12 (Southfield, Oakland), HD-7 and HD-8 (Oakland) and HD-11
(Macomb) cross county lines and are partial.
"""
import html
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

TOTALVOTE = "https://michigan.totalvote.com"

_CONTEST = re.compile(r"<h1>([^<]*?) - <br>VOTE FOR[^<]*</h1>")
_CANDIDATE = re.compile(r'display-results-box-d">\s*<h1>(.*?)</h1>\s*<h2 class="([^"]*)">.*?'
                        r'display-results-box-f">\s*<h1>([\d,]+)</h1>', re.S)


def parse_totalvote(page: str, *, source_id: str, county: str, whole: frozenset) -> list[Contest]:
    updated = re.search(r"Results Last Updated:\s*([\d/]+ [\d:]+ [AP]M)", page)
    updated_at = (datetime.strptime(updated.group(1), "%m/%d/%Y %I:%M:%S %p").isoformat() + "-05:00"
                  if updated else None)
    heads = list(_CONTEST.finditer(page))
    contests = []
    for i, head in enumerate(heads):
        chunk = page[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(page)]
        title = re.sub(r"\s+", " ", html.unescape(head.group(1))).strip()
        kind = names.office_type(title)
        district = names.district(title)
        reported = re.search(r"Precincts Reported: (\d+) / (\d+)", chunk)
        choices = [Choice(re.sub(r"\s+", " ", html.unescape(name)).strip(), names.to_int(votes), names.party(party),
                          choice_id=re.sub(r"\s+", " ", html.unescape(name)).strip())
                   for name, party, votes in _CANDIDATE.findall(chunk)]
        complete = kind in ("local", "judicial") or (kind, district) in whole
        contest = Contest(
            source=source_id, contest_id=title, state="MI", title=title, office_type=kind, district=district,
            jurisdiction=f"{county} County", scope="complete" if complete else "partial",
            reporting=Reporting(int(reported.group(1)), int(reported.group(2))) if reported else Reporting(),
            feed_updated_at=updated_at, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


_WASHTENAW_RACE = re.compile(r'class="headertr" colspan="4">([^<]+)</td>')
# Candidate, then early / absentee / election-day votes (skipped) and the total.
_WASHTENAW_ROW = re.compile(r'class="bb1[^"]*">(?:&nbsp;)*([^<]+)</td>'
                            r'(?:<td[^>]*>[\d,]*</td>){3}<td[^>]*>([\d,]+)</td>')


def parse_washtenaw(page: str, *, whole: frozenset) -> list[Contest]:
    """Washtenaw's index page: every race in one summary table (early, absentee, election day, total, percent).
    Precincts counted is only given countywide, so it's shown as labeled text, not a per-race percentage."""
    created = re.search(r"This report created: \w+, (\w+ \d+, \d+ [\d:]+ [AP]M)", page)
    updated_at = (datetime.strptime(created.group(1), "%b %d, %Y %I:%M:%S %p").isoformat() + "-05:00"
                  if created else None)
    counted = re.search(r"Precincts Total:.*?([\d,]+).*?Precincts Fully Counted:.*?([\d,]+)", page, re.S)
    heads = list(_WASHTENAW_RACE.finditer(page))
    contests = []
    for i, head in enumerate(heads):
        chunk = page[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(page)]
        title = re.sub(r"\s+", " ", html.unescape(head.group(1))).strip()
        if title.lower().startswith("straight party"):
            continue
        kind, district = names.office_type(title), names.district(title)
        if re.search(r"\b(proposal|millage|question)\b", title, re.I):
            kind, district = "measure", names.measure_id(title) or names.fold(title)[:60]
        choices = []
        for name, total in _WASHTENAW_ROW.findall(chunk):
            name = re.sub(r"\s+", " ", html.unescape(name)).strip()
            if name.lower().endswith("write-ins"):
                continue
            name = names.yes_no(name) if kind == "measure" else name
            choices.append(Choice(name, names.to_int(total), choice_id=name))
        complete = kind in ("local", "judicial", "measure") or (kind, district) in whole
        reporting = Reporting()
        if counted:
            total, done = names.to_int(counted.group(1)), names.to_int(counted.group(2))
            reporting = Reporting(done, total, as_percent=False,
                                  text=f"Countywide, {done} of {total} precincts fully counted")
        contest = Contest(
            source="mi.washtenaw", contest_id=title, state="MI", title=title, office_type=kind, district=district,
            jurisdiction="Washtenaw County", scope="complete" if complete else "partial", reporting=reporting,
            feed_updated_at=updated_at, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Wayne(Source):
    id = "mi.wayne"
    state = "MI"
    level = "county"
    county = "Wayne"
    title = "Wayne County results (TotalVote)"
    site_name = "Wayne County Clerk"
    url = f"{TOTALVOTE}/Wayne"
    platform = "TotalVote (HTML)"
    tiers = frozenset({1, 2, 4})
    whole_districts = frozenset({("federal_house", "13"), ("state_senate", "2"), ("state_house", "26"),
                                 ("state_house", "27")})
    # Congress, State Senate, State Representative. Statewide races (ST) would only be Wayne's share.
    categories = ("CON", "SEN", "REP")

    def pull(self, fetch):
        home = fetch.get(self.url, expect="text")
        if config.ELECTION_DATE.strftime("%B %-d, %Y").upper() not in home.upper():
            raise NotPublished(f"TotalVote isn't showing the {config.ELECTION_DATE} election")
        contests = []
        for category in self.categories:
            page = fetch.get(f"{self.url}/ResultsSW.aspx", params={"type": category, "cid": "05", "map": ""},
                             expect="text")
            contests += parse_totalvote(page, source_id=self.id, county=self.county, whole=self.whole_districts)
        return contests


class Washtenaw(Source):
    id = "mi.washtenaw"
    state = "MI"
    level = "county"
    county = "Washtenaw"
    title = "Washtenaw County election results"
    site_name = "Washtenaw County Clerk"
    platform = "Washtenaw County results pages (HTML)"
    tiers = frozenset({4})
    # No WFP state or federal district lies wholly in Washtenaw (HD-23 also has Wayne precincts).
    whole_districts = frozenset()
    url = "https://electionresults.ewashtenaw.org/electionreporting/" \
          f"{config.ELECTION_DATE.strftime('%b').lower()}{config.ELECTION_DATE.year}/index.jsp"

    def pull(self, fetch):
        page = fetch.get(self.url, expect="text")
        if config.ELECTION_DATE.strftime("%B %-d, %Y") not in page:
            raise NotPublished(f"{self.url} isn't the {config.ELECTION_DATE} election")
        return parse_washtenaw(page, whole=self.whole_districts)


SOURCES = [Wayne(), Washtenaw()]
