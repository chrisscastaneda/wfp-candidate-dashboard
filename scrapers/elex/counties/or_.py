"""Oregon county sources: Multnomah County's ranked-choice results.

Multnomah uses ranked-choice voting for its county offices and Portland's city offices. Oregon's state results list
those contests with no votes; the county posts the tabulation at rcvresults.multco.us:

  /                                  -> one section per election ("November 3, 2026 General Election"), each contest
                                        with its reports newest first: /Reports/<run id>/<Contest_Name>
                                        ("Preliminary Results 3", ..., "Final Results")
  /Reports/<run id>/<Contest_Name>   -> links to the tabulation's summary JSON (RCTab format) on a signed, expiring
                                        blob URL: {config: {office, threshold}, results: [{round, tally: {name: votes}}]}

Each candidate shows their total in the last round they were in (the final round for those still counted). The
candidates elected hold the threshold and lead the rest, and an eliminated candidate had the fewest votes when cut, so
the top `vote_for` (one, or three for Portland's council districts) are the tabulation's winners. Counts are rounded,
since transfers between rounds are fractional.
"""
import html
import re
from datetime import datetime
from urllib.parse import quote

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

MULTNOMAH_RCV = "https://rcvresults.multco.us"


def latest_reports(home: str, election_heading: str) -> dict[str, tuple[str, str]]:
    """Contest name -> (report path, report label), newest report per contest, for one election's section."""
    start = home.find(election_heading)
    if start < 0:
        return {}
    later = re.search(r"[A-Z][a-z]+ \d{1,2}, \d{4} [A-Z][a-z]+ Election", home[start + len(election_heading):])
    section = home[start:start + len(election_heading) + later.start()] if later else home[start:]
    out = {}
    for path, label in re.findall(r'href="(/Reports/[^"]+)"[^>]*>\s*([^<]+?)\s*<', section):
        contest = html.unescape(path.rsplit("/", 1)[1]).replace("_", " ")
        out.setdefault(contest, (path, label))  # listed newest first
    return out


def parse_tabulation(summary: dict, *, title: str, label: str, published: str | None) -> Contest:
    rounds = summary.get("results") or []
    last: dict[str, float] = {}
    for rnd in rounds:  # each candidate's total in the last round they were still in
        for name, votes in rnd["tally"].items():
            last[name] = float(votes)
    seats = re.search(r"(\d+) Seats? Up for Election", title)
    choices = [Choice(name, round(votes), choice_id=name) for name, votes in last.items()
               if not name.lower().startswith("uncertified write")]
    choices.sort(key=lambda c: c.votes, reverse=True)
    office = (summary.get("config") or {}).get("office") or title
    contest = Contest(
        source="or.multnomah", contest_id=office, state="OR",
        title=f"{office} (ranked-choice, round {len(rounds)} of {len(rounds)})", office_type="local",
        district=names.district(office), jurisdiction="Multnomah County",
        vote_for=int(seats.group(1)) if seats else 1,
        reporting=Reporting(as_percent=False, text=f"Ranked-choice tabulation, {label.lower()}"),
        feed_updated_at=published, choices=choices)
    contest.fill_percentages()
    return contest


class MultnomahRcv(Source):
    id = "or.multnomah"
    state = "OR"
    level = "county"
    county = "Multnomah"
    title = "Multnomah County ranked-choice results"
    site_name = "Multnomah County Elections"
    url = MULTNOMAH_RCV + "/"
    platform = "Multnomah RCV results (RCTab JSON)"
    tiers = frozenset({4})

    def pull(self, fetch):
        heading = f"{config.ELECTION_DATE.strftime('%B %-d, %Y')} General Election"
        reports = latest_reports(fetch.get(self.url, expect="text"), heading)
        if not reports:
            raise NotPublished(f"no {heading} section on {self.url}")
        contests = []
        for name, (path, label) in reports.items():
            page = fetch.get(MULTNOMAH_RCV + quote(path, safe="/,()-_"), expect="text")
            link = re.search(r'href="([^"]+\.json[^"]*)"', page)
            if not link:
                continue
            seats = re.search(r"\d+ Seats? Up for Election", page)
            stamp = re.search(r"Published: (\w+ \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M)", page)
            published = (datetime.strptime(stamp.group(1), "%B %d, %Y %I:%M %p").isoformat() + "-08:00"
                         if stamp else None)
            summary = fetch.get(html.unescape(link.group(1)).replace(" ", "%20"))
            contest = parse_tabulation(summary, title=f"{name} {seats.group(0) if seats else ''}", label=label,
                                       published=published)
            contest.url = MULTNOMAH_RCV + path
            contests.append(contest)
        return contests


SOURCES = [MultnomahRcv()]
