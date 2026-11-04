"""Connecticut Secretary of the State election results (ctemspublic.tgstg.net), an Angular app over static JSON:

  ng-app/data/Elections.json                                   -> [{ID, Name: "11/03/2026 -- ..."}]
  ng-app/data/election/<id>/Version.json                       -> {"Version": n}
  ng-app/data/election/<id>/<n>/Lookupdata.json                -> offices, candidates, parties
  ng-app/data/election/<id>/<n>/stateVotes_Electiondata.json   -> statewide totals per office and candidate line
  ng-app/data/election/<id>/<n>/election_Electiondata.json     -> statewide precincts reporting

Connecticut has fusion voting: a candidate appears once per party line (Jahana Hayes on Democratic and Working
Families). Lines are combined into one choice per candidate, with the per-line votes in `party_lines`.
"""
import re
from collections import OrderedDict
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

BASE = "https://ctemspublic.tgstg.net/ng-app/data"

_TYPES = {"C": "federal_house", "S": "state_senate", "A": "state_house"}


def find_election(elections: list[dict]) -> str:
    for e in elections:
        try:
            when = datetime.strptime(e["Name"].split(" -- ")[0].strip(), "%m/%d/%Y").date()
        except ValueError:
            continue
        if when == config.ELECTION_DATE:
            return e["ID"]
    raise NotPublished(f"no {config.ELECTION_DATE} election listed")


def _reporting(text: str | None) -> Reporting:
    m = re.search(r"([\d,]+) of ([\d,]+)", text or "")
    return Reporting(names.to_int(m.group(1)), names.to_int(m.group(2)), text=text) if m else Reporting(text=text)


def parse(lookup: dict, votes: dict, election: dict) -> list[Contest]:
    offices = {k: v for entry in lookup["officeList"] for k, v in entry.items()}
    candidates, parties = lookup["candidateIds"], lookup["partyIds"]
    reporting = _reporting(election.get("PR"))
    contests = []
    for office_id, lines in votes.items():
        office = offices.get(office_id)
        if not office:
            continue
        kind = _TYPES.get(office.get("OT")) or names.office_type(office["NM"])
        by_name: dict[str, Choice] = OrderedDict()
        for line in lines:
            for cand_id, tally in line.items():
                cand = candidates.get(cand_id, {})
                party = parties.get(cand.get("P"), {})
                code = names.party(party.get("NM")) or party.get("CD")
                name = cand.get("NM") or cand_id
                choice = by_name.setdefault(name, Choice(name, 0, code, choice_id=name, party_lines={}))
                n = names.to_int(tally.get("V"))
                choice.votes += n
                choice.party_lines[code or "?"] = choice.party_lines.get(code or "?", 0) + n
        contest = Contest(
            source="ct", contest_id=office_id, state="CT", title=office["NM"], office_type=kind,
            district=(office.get("D") or None) if office.get("D") not in ("", "0") else None,
            jurisdiction="Connecticut", reporting=reporting, choices=list(by_name.values()))
        contest.fill_percentages()
        contests.append(contest)
    return contests


class Connecticut(Source):
    id = "ct"
    state = "CT"
    title = "CT Secretary of the State election results"
    site_name = "Connecticut Secretary of the State"
    url = "https://ctemspublic.tgstg.net/#/home"
    platform = "CT EMS static JSON"
    tiers = frozenset({1, 2, 4})
    local_races = False  # town questions only; no municipal offices in a state election

    def pull(self, fetch):
        election_id = find_election(fetch.get(f"{BASE}/Elections.json"))
        version = fetch.get(f"{BASE}/election/{election_id}/Version.json")["Version"]
        path = f"{BASE}/election/{election_id}/{version}"
        return parse(fetch.get(f"{path}/Lookupdata.json"), fetch.get(f"{path}/stateVotes_Electiondata.json"),
                     fetch.get(f"{path}/election_Electiondata.json"))


SOURCES = [Connecticut()]
