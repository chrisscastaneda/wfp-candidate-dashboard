"""Each state legislative seat's previous general election result, for rating 2026 races before the fact.

  .venv/bin/python analysis/prior_results.py      # writes data/ratings/state_leg_prior.csv

Sources (all on the 2026 district lines, which haven't changed since 2024):
  NY  2024 general, Senate and Assembly. Copied by hand from the NYS Board of Elections results database
      (results.elections.ny.gov, search: 2024, office "State Senator" / "Member of Assembly") into
      data/ratings/ny_legislature_2024.txt. Its party labels list every line, e.g. "D/W" = Democratic and WFP.
  CT  2024 general, both chambers, from the Secretary of the State's results site (same JSON as scrapers/elex/states/ct.py).
  PA  2024 general for the House and odd Senate districts; 2022 for even Senate districts (four-year terms, so the even
      districts on the 2026 ballot were last up in 2022). From the Department of State API (scrapers/elex/states/pa.py).
  CO  2024 general, plus 2022 for Senate seats not up in 2024, from the Secretary of State's Clarity results site
      (scrapers/elex/platforms/clarity.py).
  GA  2024 general, both chambers (two-year terms), from the Secretary of State's results site
      (scrapers/elex/platforms/enhanced_voting.py). Georgia redrew its maps in December 2023, before the 2024 election.
  CA, OR, NM, WI, AZ, OH, MA  Copied by hand from Wikipedia's district results tables (each section of data/ratings/wikipedia_legislature.txt
      names its page): CA Assembly 2024 and Senate 2022 (the even seats on the 2026 ballot); OR House 2024 and
      Senate 2022 and 2024; NM House 2024 (the NM Senate isn't up until 2028); WI Assembly 2024 (vote shares only, so
      stored as hundredths of a percent; the WI Senate is left out, since its 2026 seats were last elected in 2022 on
      the maps replaced in 2024); AZ House and Senate 2024 (two House members per district); OH House 2024 (the OH
      Senate is left out: its 2026 seats were last elected in 2022, on maps replaced in 2023); MA House 2024 (named
      districts, keyed by district_key()). The states' own archives are PDF or spreadsheet downloads. California's general elections
      are top-two, so some seats had two Democrats or two Republicans last time.

Senate seats appear in whichever year they were last on the ballot; a seat in both years keeps the later one.

One row per candidate, votes summed across party lines. `seats` is how many the district elects. `party` is D or R when the candidate ran on that major
party's line (the first one listed in NY), otherwise the first line's code.
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scrapers"))

from elex import config  # noqa: E402
from elex.fetch import Fetcher  # noqa: E402
from elex.platforms.clarity import ClaritySource  # noqa: E402
from elex.platforms.enhanced_voting import EnhancedVotingSource  # noqa: E402
from elex.states import ct, pa  # noqa: E402

OUT = REPO / "data" / "ratings" / "state_leg_prior.csv"
NY_FILE = REPO / "data" / "ratings" / "ny_legislature_2024.txt"
WIKI_FILE = REPO / "data" / "ratings" / "wikipedia_legislature.txt"
CHAMBERS = ("state_house", "state_senate")


def major(lines):
    """'D' or 'R' if any of the candidate's lines is a major party, else the first line."""
    codes = [{"DEM": "D", "REP": "R"}.get(x.upper(), x.upper()) for x in lines if x]
    return next((c for c in codes if c in ("D", "R")), codes[0] if codes else "")


def ny_rows():
    chamber = None
    for line in NY_FILE.read_text().splitlines():
        if line.startswith("# "):
            chamber = line[2:].strip()
            continue
        if not line.strip():
            continue
        district, _total, cands = line.split(":", 2)
        for cand in cands.split(";"):
            name, lines, votes = cand.split("~")
            yield dict(state="NY", chamber=chamber, district=str(int(district)), seats=1, year=2024, candidate=name,
                       party=major(lines.split("/")), lines=lines, votes=int(votes),
                       source="results.elections.ny.gov")


def district_key(text):
    """'7' -> '7'; Massachusetts names -> '16th middlesex', 'barnstable, dukes and nantucket'. Shared with
    analysis/competitiveness.py so both sides of the lookup normalize the same way."""
    text = text.strip()
    if text.isdigit():
        return str(int(text))
    text = re.sub(r"\bdistrict\b", "", text.lower().replace("&", "and"))
    return re.sub(r"\s+", " ", text).strip(" ,")


def wiki_rows():
    """Sections '# <state> <chamber> <year> <url>', then 'district:name~party~votes;...' lines."""
    for line in WIKI_FILE.read_text().splitlines():
        if line.startswith("# ("):
            continue  # a note about the section above
        if line.startswith("# "):
            state, chamber, year, url = line[2:].split()
            continue
        if not line.strip():
            continue
        district, cands = line.split(":", 1)
        for cand in cands.split(";"):
            name, party, votes = cand.split("~")
            seats = 2 if (state, chamber) == ("AZ", "state_house") else 1  # Arizona elects two per House district
            yield dict(state=state, chamber=chamber, district=district_key(district), seats=seats, year=int(year),
                       candidate=name,
                       party=major([party]), lines=party, votes=int(votes), source=url)


def latest_only(rows):
    """Keep each seat's most recent election (a Senate seat up in both 2022 and 2024 keeps 2024)."""
    last = {}
    for r in rows:
        key = (r["state"], r["chamber"], r["district"])
        last[key] = max(last.get(key, 0), r["year"])
    return [r for r in rows if r["year"] == last[(r["state"], r["chamber"], r["district"])]]


def pulled_rows(source, state, when, keep=lambda c: True):
    config.ELECTION_DATE = when
    fetch = Fetcher().for_source(f"prior.{source.id}")
    for c in source.pull(fetch):
        if c.office_type not in CHAMBERS or not keep(c):
            continue
        for ch in c.choices:
            if ch.name.lower().startswith("write"):
                continue
            lines = list((ch.party_lines or {}).keys()) or [ch.party or ""]
            yield dict(state=state, chamber=c.office_type, district=str(int(c.district)), seats=c.vote_for or 1,
                       year=when.year,
                       candidate=re.sub(r"\s*\(I\)$", "", ch.name.strip()), party=major(lines), lines="/".join(lines), votes=ch.votes or 0,
                       source=source.url)


def main():
    rows = list(ny_rows())
    rows += pulled_rows(ct.Connecticut(), "CT", date(2024, 11, 5))
    rows += pulled_rows(pa.Pennsylvania(), "PA", date(2024, 11, 5),
                        keep=lambda c: c.office_type == "state_house" or int(c.district) % 2 == 1)
    rows += pulled_rows(pa.Pennsylvania(), "PA", date(2022, 11, 8),
                        keep=lambda c: c.office_type == "state_senate" and int(c.district) % 2 == 0)
    colorado = ClaritySource("co", "CO", "Colorado SoS results", "Colorado Secretary of State", "CO")
    rows += pulled_rows(colorado, "CO", date(2024, 11, 5))
    rows += pulled_rows(colorado, "CO", date(2022, 11, 8), keep=lambda c: c.office_type == "state_senate")
    georgia = EnhancedVotingSource("ga", "GA", "Georgia SoS results", "Georgia Secretary of State",
                                   "https://results.sos.ga.gov", "Georgia")
    rows += pulled_rows(georgia, "GA", date(2024, 11, 5))
    rows += wiki_rows()
    rows = latest_only(rows)
    rows.sort(key=lambda r: (r["state"], r["chamber"], r["district"].zfill(4), -r["votes"]))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    seats = {(r["state"], r["chamber"], r["district"]) for r in rows}
    for st in ("NY", "CT", "PA", "CO", "CA", "OR", "GA", "NM", "WI", "AZ", "OH", "MA"):
        print(st, {ch: sum(1 for s in seats if s[0] == st and s[1] == ch) for ch in CHAMBERS})
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} candidates")


if __name__ == "__main__":
    main()
