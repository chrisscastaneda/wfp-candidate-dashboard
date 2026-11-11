"""Louisiana Secretary of State live results (voterportal.sos.la.gov/graphical). The page reads JSON "blobs":

  ElectionResults/ElectionResults/Data?blob=ElectionDates.htm
      -> Dates.Date[]: ElectionDate ("11/03/2026"), ResultsOfficial
  ...?blob=<yyyymmdd>/RacesCandidates_Multiparish.htm
      -> Races.Race[]: ID, SpecificTitle ("Judge -- Criminal District Court, Section D"), NumberToBeElected,
         Choice[]: ID, Desc ("Simone Levine (DEM)")
  ...?blob=<yyyymmdd>/Votes_Multiparish.htm
      -> Races.Race[]: ID, PrecinctsReporting, PrecinctsExpected, Choice[]: ID, VoteTotal, Outcome

The multiparish files hold every federal, state and judicial race with statewide totals, including single-parish
courts like Orleans's. Parish offices and local measures are in RacesCandidates/ByParish_<nn>.htm and
VotesParish/Votes_<nn>.htm; WFP's Louisiana endorsement doesn't need them.
"""
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data"
_PARTY = re.compile(r"\s*\(([A-Z]+)\)\s*$")


def parse(races: dict, votes: dict, *, updated: str | None = None) -> list[Contest]:
    counts = {r["ID"]: r for r in (votes.get("Races") or {}).get("Race") or []}
    contests = []
    for race in (races.get("Races") or {}).get("Race") or []:
        title = re.sub(r"\s+", " ", race["SpecificTitle"]).strip()
        tally = counts.get(race["ID"], {})
        by_id = {c["ID"]: c for c in tally.get("Choice") or []}
        is_measure = bool(re.match(r"(?i)(CA No\.|PW |amendment|proposition)", title)) or \
            {c["Desc"].upper() for c in race["Choice"]} <= {"YES", "NO", "FOR", "AGAINST"}
        choices = []
        for c in race["Choice"]:
            party = _PARTY.search(c["Desc"])
            name = _PARTY.sub("", c["Desc"]).strip()
            choices.append(Choice(names.yes_no(name) if is_measure else name,
                                  names.to_int(by_id.get(c["ID"], {}).get("VoteTotal")),
                                  names.party(party.group(1)) if party and party.group(1) != "NOPTY" else None,
                                  choice_id=c["ID"]))
        kind = "measure" if is_measure else names.office_type(title)
        if re.match(r"(?i)(district |city |magistrate )?judge\b", title):
            kind = "judicial"
        contest = Contest(
            source="la", contest_id=race["ID"], state="LA", title=title, office_type=kind,
            district=(names.measure_id(title) or names.fold(title)[:60]) if is_measure else names.district(title),
            jurisdiction="Louisiana", vote_for=names.to_int(race.get("NumberToBeElected")) or 1,
            reporting=Reporting(names.to_int(tally.get("PrecinctsReporting")),
                                names.to_int(tally.get("PrecinctsExpected"))),
            feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Louisiana(Source):
    id = "la"
    state = "LA"
    title = "Louisiana SoS live results"
    site_name = "Louisiana Secretary of State"
    url = "https://voterportal.sos.la.gov/graphical"
    platform = "LA SoS results (JSON blobs)"
    tiers = frozenset({1, 2, 3, 4})

    def pull(self, fetch):
        dates = fetch.get(BASE, params={"blob": "ElectionDates.htm"})
        wanted = config.ELECTION_DATE.strftime("%m/%d/%Y")
        if not any(d.get("ElectionDate") == wanted for d in (dates.get("Dates") or {}).get("Date") or []):
            raise NotPublished(f"no {wanted} election listed")
        folder = config.ELECTION_DATE.strftime("%Y%m%d")
        races = fetch.get(BASE, params={"blob": f"{folder}/RacesCandidates_Multiparish.htm"})
        votes = fetch.get(BASE, params={"blob": f"{folder}/Votes_Multiparish.htm"})
        stamp = (races.get("Races") or {}).get("WriteTime")
        return parse(races, votes, updated=stamp + "-06:00" if stamp else None)


SOURCES = [Louisiana()]
