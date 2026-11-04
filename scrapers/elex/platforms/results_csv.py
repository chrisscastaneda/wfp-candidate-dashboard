"""The results vendor behind New Mexico's and Nebraska's sites. CSV exports by office group:

  <base>/resultsCSV.aspx?text=All&type=<GROUP>&map=CTY

One row per candidate per race, with statewide totals. The sites only serve the current election. Nebraska's
`type=All` covers every group; New Mexico's returns nothing, so NM lists its groups. Groups can overlap (NM's STATE
includes its CTY races); rows are de-duplicated by race and candidate.
"""
import csv
import io
import re

from .. import names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source


def _reporting(text: str) -> Reporting:
    m = re.search(r"(\d+)\s*/\s*(\d+)", text or "")  # "0/2204" or Nebraska's '="0/1322"'
    return Reporting(int(m.group(1)), int(m.group(2)), text=f"{m.group(1)} of {m.group(2)} precincts") if m \
        else Reporting(text=text or None)


def parse(text: str, *, source_id: str, state: str, jurisdiction: str, seen: set | None = None) -> list[Contest]:
    seen = set() if seen is None else seen
    contests: dict[str, Contest] = {}
    for row in csv.DictReader(io.StringIO(text)):
        key = (row["RaceID"], row["CandidateID"])
        if not row.get("RaceID") or key in seen:
            continue
        seen.add(key)
        race = row["RaceName"].strip()
        area = (row.get("AreaNum") or "").strip()
        title = f"{race} {area.title()}".strip() if area and area.lower() not in race.lower() else race
        contest = contests.get(row["RaceID"])
        if contest is None:
            # Judicial retention questions stay "judicial"; amendments and bond questions are measures.
            kind = "measure" if re.search(r"\b(amendment|question)\b", race, re.I) else names.office_type(race)
            if kind == "measure":
                district = names.measure_id(race) or names.fold(race)[:60]
            else:
                district = names.district(area or race)
            contest = contests[row["RaceID"]] = Contest(
                source=source_id, contest_id=row["RaceID"], state=state, title=title, office_type=kind,
                district=district,
                jurisdiction=jurisdiction, vote_for=names.to_int(row.get("VoteFor")) or 1,
                reporting=_reporting(row.get("PrecinctsReporting")),
                feed_updated_at=(row.get("CurrentDateTime") or None))
        name = re.sub(r"\s+", " ", row["CandidateName"]).strip()
        contest.choices.append(Choice(
            names.yes_no(name) if contest.office_type == "measure" or name.lower() in ("yes", "no", "for",
                                                                                         "against") else name,
            names.to_int(row.get("CandidateVotes")), names.party(row.get("PartyCode")), choice_id=row["CandidateID"]))
    # CandidatePercentage is a fraction (0.4513), so percentages come from the votes instead.
    for contest in contests.values():
        contest.fill_percentages()
    return list(contests.values())


class ResultsCsvSource(Source):
    platform = "results CSV (NM/NE vendor)"

    def __init__(self, id, state, title, site_name, base, groups, tiers=(1, 2, 3, 4), local_races=True):
        self.id, self.state, self.title, self.site_name, self.local_races = id, state, title, site_name, local_races
        self.base, self.groups, self.tiers = base.rstrip("/"), list(groups), frozenset(tiers)
        self.url = self.base + "/"

    def pull(self, fetch):
        contests, seen = [], set()
        for group in self.groups:
            text = fetch.get(f"{self.base}/resultsCSV.aspx", params={"text": "All", "type": group, "map": "CTY"},
                             expect="text")
            contests += parse(text, source_id=self.id, state=self.state, jurisdiction=self.title, seen=seen)
        if not contests:
            raise NotPublished("CSV exports are empty")
        return contests
