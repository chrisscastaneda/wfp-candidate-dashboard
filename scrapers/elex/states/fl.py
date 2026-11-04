"""Florida Division of Elections election-night results (floridaelectionwatch.gov).

The site's Downloads page links a tab-delimited file of every state-run contest, one row per candidate per county:

  https://flelectionfiles.floridados.gov/enightfilespublic/<YYYYMMDD>_ElecResultsFL.txt?v=<n>
  columns: RaceCode (USS, USR, STS, STR, GOV, AMD, ...), RaceName, CountyName, Juris1num (district), Precincts,
           PrecinctsReporting, CanNameFirst/Middle/Last, PartyCode, CanVotes

The plain URL serves a stale cached copy (Nov 2's zeros on election night), so the link is read from the Downloads
page each time, with the `v` number the site adds. County rows are summed per contest.
"""
import csv
import io
import re
from collections import OrderedDict

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

SITE = "https://floridaelectionwatch.gov/"


def parse(text: str) -> list[Contest]:
    contests: dict[tuple, Contest] = OrderedDict()
    precincts: dict[tuple, dict[str, tuple[int, int]]] = {}  # contest -> county -> (reporting, total)
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        code, title = row["RaceCode"].strip(), re.sub(r"\s+", " ", row["RaceName"]).strip()
        district = (row.get("Juris1num") or "").strip().lstrip("0") or None
        key = (code, title, district, (row.get("Juris2num") or "").strip())
        is_measure = code == "AMD"
        contest = contests.get(key)
        if contest is None:
            contest = contests[key] = Contest(
                source="fl", contest_id="/".join(filter(None, key)), state="FL", title=title,
                office_type="measure" if is_measure else names.office_type(title),
                district=names.measure_id(title) or names.fold(title)[:60] if is_measure
                else district or names.district(title),
                jurisdiction="Florida")
        precincts.setdefault(key, {})[row["CountyName"]] = (names.to_int(row.get("PrecinctsReporting")),
                                                           names.to_int(row.get("Precincts")))
        name = " ".join(p.strip() for p in (row["CanNameFirst"], row["CanNameMiddle"], row["CanNameLast"])
                        if p and p.strip())
        if is_measure or code in ("SCJ", "DCA"):
            name = names.yes_no(name)
        party = names.party(row.get("PartyCode")) if row.get("PartyCode") not in ("NOP", "") else None
        choice = next((c for c in contest.choices if c.choice_id == name), None)
        if choice is None:
            choice = Choice(name, 0, party, choice_id=name)
            contest.choices.append(choice)
        choice.votes += names.to_int(row.get("CanVotes"))
    for key, contest in contests.items():
        done = sum(r for r, _ in precincts[key].values())
        total = sum(t for _, t in precincts[key].values())
        contest.reporting = Reporting(done, total, text=f"{done:,} of {total:,} precincts" if total else None)
        contest.fill_percentages()
    return list(contests.values())


class Florida(Source):
    id = "fl"
    state = "FL"
    title = "Florida Division of Elections election-night file"
    site_name = "Florida Division of Elections"
    url = SITE
    platform = "FL results file (tab-delimited)"
    tiers = frozenset({1, 2})

    def pull(self, fetch):
        downloads = fetch.get(SITE + "Downloads", expect="text")
        stamp = config.ELECTION_DATE.strftime("%Y%m%d")
        link = re.search(rf'href="([^"]*/{stamp}_ElecResultsFL\.txt[^"]*)"', downloads)
        if not link:
            raise NotPublished(f"no {stamp} results file linked on the Downloads page")
        return parse(fetch.get(link.group(1).replace("&amp;", "&"), expect="text"))


SOURCES = [Florida()]
