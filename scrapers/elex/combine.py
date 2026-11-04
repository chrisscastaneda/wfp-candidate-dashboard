"""District races summed from county results, for states whose own results site we can't read (New York).

Each county source reports its share of the Assembly, Senate and U.S. House races on its ballot, marked partial. When
every county in a district has a working source, the shares add up to the whole district:

  data/ny_district_counties.json   district -> counties (from the Census Bureau's block equivalency files)

A county source that is healthy but doesn't list the district is taken to have no voters in it (the Census files
include empty water blocks, like Lake Erie's in AD-150). A county with no source, or whose source isn't healthy, leaves
the district out. Candidates are joined across counties by first initial and surname ("Shelley Mayer" and
"Shelley B. Mayer").

The result is stored like any other source ("ny.counties") so matching and publishing treat it normally.
"""
import json
import re
from collections import OrderedDict

from . import config, names
from .model import NOT_MODIFIED, OK, Choice, Contest, Reporting
from .source import Source

NYC_BOROUGHS = {"Bronx", "Kings", "New York", "Queens", "Richmond"}
_KINDS = ("state_house", "state_senate", "federal_house")


class CountySums(Source):
    """Not pulled: run.py builds its contests from the other sources after they're stored."""
    id = "ny.counties"
    state = "NY"
    level = "county"
    county = None
    title = "New York districts summed from county results"
    site_name = "New York county boards of elections (summed)"
    platform = "derived"
    tiers = frozenset({1, 2})
    derived = True
    mapping_file = config.DATA_DIR / "ny_district_counties.json"

    def pull(self, fetch):
        raise NotImplementedError("derived from other sources; see combine.build")


SOURCES = [CountySums()]


def _county_sources(sources) -> dict[str, str]:
    """County name -> source id, for New York's county sources (NYC's boroughs share one)."""
    out = {}
    for s in sources:
        if s.state != "NY" or s.level != "county" or getattr(s, "derived", False):
            continue
        if s.county == "NYC":
            out.update({b: s.id for b in NYC_BOROUGHS})
        elif s.county:
            out[s.county] = s.id
    return out


def _usable(record: dict | None) -> bool:
    """A county source whose last pull worked and has contests. A county that hasn't posted, or blocked us, can't
    stand for "no voters in this district"."""
    return bool(record and record.get("status") in (OK, NOT_MODIFIED) and record.get("contests"))


def _person(name: str) -> str:
    """'Shelley B. Mayer' -> 's|mayer'."""
    first = names.fold(name).split()
    return f"{first[0][0] if first else ''}|{names.surname(name) or names.fold(name)}"


def _sum(parts: list[tuple[str, Contest]], kind: str, district: str) -> Contest:
    """One contest from each county's share. `parts` is [(county, contest)]."""
    by_key: dict[str, Choice] = OrderedDict()
    for _, contest in parts:
        for ch in contest.choices:
            if ch.name.lower().startswith("write-in") and not ch.votes:
                continue
            key = _person(ch.name)
            have = by_key.get(key)
            if have is None:
                by_key[key] = Choice(ch.name, ch.votes, ch.party, choice_id=ch.name,
                                     party_lines=dict(ch.party_lines) if ch.party_lines else None)
                continue
            have.votes += ch.votes
            if len(ch.name) > len(have.name):
                have.name = have.choice_id = ch.name  # the fuller spelling ("Shelley B. Mayer")
            have.party = have.party or ch.party
            for code, votes in (ch.party_lines or {}).items():
                have.party_lines = have.party_lines or {}
                have.party_lines[code] = have.party_lines.get(code, 0) + votes
    counties = [county for county, _ in parts]
    title = re.sub(r"\s*\*$", "", parts[0][1].title)
    stamps = [c.feed_updated_at for _, c in parts if c.feed_updated_at]
    listed = counties[0] if len(counties) == 1 else ", ".join(counties[:-1]) + " and " + counties[-1]
    text = f"Summed from {listed} county results"
    contest = Contest(
        source=CountySums.id, contest_id=f"{kind}.{district}", state="NY", title=title, office_type=kind,
        district=district, jurisdiction="New York", vote_for=parts[0][1].vote_for,
        reporting=Reporting(as_percent=False, text=text), feed_updated_at=min(stamps) if stamps else None,
        choices=list(by_key.values()))
    contest.fill_percentages()
    return contest


def build(latest: dict[str, dict], sources, mapping: dict | None = None) -> tuple[list[Contest], list[str]]:
    """Summed contests, and one line per district left out (for the run log)."""
    if mapping is None:
        mapping = json.loads(CountySums.mapping_file.read_text())
    by_county = _county_sources(sources)
    contests, skipped = [], []
    for kind in _KINDS:
        for district, counties in mapping.get(kind, {}).items():
            missing = [c for c in counties if c not in by_county or not _usable(latest.get(by_county[c]))]
            if missing:
                skipped.append(f"{kind} {district}: no results for {', '.join(missing)}")
                continue
            parts, seen = [], set()
            for county in counties:
                sid = by_county[county]
                if sid in seen:
                    continue  # NYC's boroughs are one source
                seen.add(sid)
                found = [c for c in latest[sid].get("contests", [])
                         if c.office_type == kind and c.district == district and c.choices]
                if len(found) > 1:
                    skipped.append(f"{kind} {district}: {sid} has {len(found)} contests for it")
                    parts = []
                    break
                if found:
                    parts.append(("New York City" if sid == by_county.get("Kings") else county, found[0]))
            if not parts:
                continue
            if len(parts) == 1 and parts[0][1].scope == "complete":
                continue  # already whole in its own source (NYC-only districts)
            contests.append(_sum(parts, kind, district))
    return contests, skipped
