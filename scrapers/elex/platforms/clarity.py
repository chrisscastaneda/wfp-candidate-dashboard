"""Clarity ENR (Scytl) results sites: Colorado, South Carolina, Florida's mirror, and many county sites.

  results.enr.clarityelections.com/<site>/elections.json                      -> [{EID, Date, ...}] (gzip)
  .../<site>/<EID>/current_ver.txt                                            -> version number
  .../<site>/<EID>/<ver>/json/en/summary.json                                 -> one entry per contest
  .../<site>/<EID>/<ver>/json/en/electionsettings.json                        -> participating counties

<site> is a state ("CO") or a county ("TX/Denton"). A state election lists its county sub-elections as
"Name|EID|ver|updated|..." under settings.electiondetails.participatingcounties; those carry the county races.
Name the counties to read in `counties`. County files repeat the county's share of state contests; those are
skipped, so only county races come from them.
"""
import re
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://results.enr.clarityelections.com"
_MEASURE = re.compile(r"\b(ballot (issue|question|measure)|amendment|proposition|referred measure|question \d)",
                      re.I)


def find_election(elections: list[dict]) -> str:
    for e in elections or []:
        try:
            when = datetime.strptime(e["Date"].split()[0], "%m/%d/%Y").date()
        except (KeyError, ValueError):
            continue
        if when == config.ELECTION_DATE:
            return e["EID"]
    raise NotPublished(f"no {config.ELECTION_DATE} election listed")


def parse(summary: list[dict], *, source_id: str, state: str, jurisdiction: str, prefix: str = "",
          skip_titles=frozenset(), updated: str | None = None, partial_shares=False) -> list[Contest]:
    """`partial_shares`: this is a county site, so its state and federal contests are only the county's share."""
    contests = []
    for item in summary:
        title = (item.get("C") or "").strip()
        if not title or names.fold(title) in skip_titles:
            continue
        # A measure by title, or by its choices ("Yes"/"No", "FOR"/"AGAINST"); retention votes stay judicial.
        labels = {names.yes_no(ch) for ch in item.get("CH") or []}
        is_measure = (bool(_MEASURE.search(title)) or (labels and labels <= {"Yes", "No"})) \
            and "retain" not in title.lower()
        kind = "measure" if is_measure else names.office_type(title)
        # Hamilton County numbers measures at the start of the title: "4  PROPOSED TAX LEVY ...".
        leading = re.match(r"(\d+)\s", title)
        choices = [Choice(names.yes_no(name) if is_measure else name, names.to_int(votes), names.party(party),
                          names.to_float(pct))
                   for name, votes, party, pct in zip(item.get("CH") or [], item.get("V") or [],
                                                      item.get("P") or [None] * 99, item.get("PCT") or [None] * 99)]
        contest = Contest(
            source=source_id, contest_id=f"{prefix}{item.get('K')}", state=state, title=title, office_type=kind,
            scope="partial" if partial_shares and (kind not in ("local", "judicial", "measure")
                                                   or (is_measure and names.STATE_PROP.search(title))) else "complete",
            district=(names.measure_id(title) or (leading.group(1) if leading else None)) if is_measure
            else names.district(title), jurisdiction=jurisdiction,
            vote_for=names.to_int(item.get("VF")) or 1,
            reporting=Reporting(names.to_int(item.get("PR")), names.to_int(item.get("TP"))),
            feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class ClaritySource(Source):
    platform = "Clarity ENR"

    def __init__(self, id, state, title, site_name, site, counties=(), tiers=(1, 2, 3, 4), level="state",
                 county=None, eid=None):
        self.id, self.state, self.title, self.site_name, self.site = id, state, title, site_name, site
        # Some counties link tonight's election from their own site but never add it to Clarity's election list
        # (elections.json is empty); `eid` is that election's id, used when the list doesn't have one.
        self.eid = eid
        self.url = f"{BASE}/{site}/{eid}/" if eid else f"{BASE}/{site}/"
        self.counties, self.tiers, self.level, self.county = list(counties), frozenset(tiers), level, county

    def _summary(self, fetch, site, eid, ver):
        return fetch.get(f"{BASE}/{site}/{eid}/{ver}/json/en/summary.json")

    def pull(self, fetch):
        try:
            eid = find_election(fetch.get(f"{BASE}/{self.site}/elections.json"))
        except NotPublished:
            if not self.eid:
                raise
            eid = self.eid
        ver = fetch.get(f"{BASE}/{self.site}/{eid}/current_ver.txt", expect="text").strip()
        if not ver.isdigit():
            raise NotPublished(f"election {eid} has no published version yet")
        # "County" in the name is what the matcher's county filter keys on (see match._in_row_county).
        jurisdiction = f"{self.county} County" if self.county else names.fold(self.title).title()
        contests = parse(self._summary(fetch, self.site, eid, ver), source_id=self.id, state=self.state,
                         jurisdiction=jurisdiction, partial_shares=self.level == "county")
        for contest in contests:
            contest.url = f"{BASE}/{self.site}/{eid}/"
        if not self.counties:
            return contests
        settings = fetch.get(f"{BASE}/{self.site}/{eid}/{ver}/json/en/electionsettings.json")
        listed = {}
        for entry in (settings.get("settings", {}).get("electiondetails", {}).get("participatingcounties") or []):
            name, county_eid, county_ver, updated, *_ = entry.split("|") + ["", "", ""]
            listed[names.fold(name)] = (name, county_eid, county_ver, updated)
        seen = frozenset(names.fold(c.title) for c in contests)
        for county in self.counties:
            if names.fold(county) not in listed:
                continue  # not posted yet; its races show as unmatched rather than hiding the state's results
            name, county_eid, county_ver, updated = listed[names.fold(county)]
            county_contests = parse(self._summary(fetch, f"{self.site}/{name}", county_eid, county_ver),
                                    source_id=self.id, state=self.state, jurisdiction=f"{county} County",
                                    prefix=f"{name}/", skip_titles=seen, updated=updated or None)
            for contest in county_contests:
                contest.url = f"{BASE}/{self.site}/{name}/{county_eid}/"
            contests += county_contests
        return contests
