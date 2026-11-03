"""Pennsylvania Department of State election returns API (www.electionreturns.pa.gov/api/ElectionReturn).

The site's pages sit behind a bot check, but its JSON API answers scripts. Every response is a JSON string that
holds more JSON, so it's decoded twice. Calls, in order:

  GetAllElections                                  -> election id/type by date (2026 General: 117, "G")
  GetOfficeNames?electionid&electiontype&isactive  -> offices on the ballot, plus the statewide reporting message
  GetOfficeData?officeId&methodName=GetOfficeDetails&... -> every district contest for one office

Reporting is only published statewide ("41 Out of 9,066 Districts"), so every contest gets that figure.
"""
import json
from datetime import datetime

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

API = "https://www.electionreturns.pa.gov/api/ElectionReturn/"

_OFFICE_TYPES = {"USS": "federal_senate", "USC": "federal_house", "STS": "state_senate", "STH": "state_house",
                 "GOV": "governor", "LTG": "lt_governor", "ATG": "attorney_general", "AUD": "auditor",
                 "TRE": "treasurer"}


def _decode(payload):
    return json.loads(payload) if isinstance(payload, str) else payload


def find_election(payload) -> tuple[str, str, str]:
    """(election id, type, isactive) for config.ELECTION_DATE, from GetAllElections."""
    elections = json.loads(_decode(payload)[0]["ElectionData"])
    for e in elections:
        if datetime.strptime(e["ElectionDate"], "%m/%d/%Y").date() == config.ELECTION_DATE:
            return e["Electionid"], e["ElectionType"], e.get("ISActive") or "0"
    raise NotPublished(f"no {config.ELECTION_DATE} election listed")


def parse_offices(payload) -> tuple[list[dict], Reporting]:
    data = _decode(payload)
    offices = data.get("Table") or []
    reporting = Reporting()
    for row in data.get("Table1") or []:
        message = json.loads(row["DashboardMessage"].strip())
        reporting = Reporting(names.to_int(message.get("ReportingDistrict")),
                              names.to_int(message.get("VotingDistrict")), names.to_float(message.get("Percentage")),
                              (message.get("DistrictMessage") or "").strip())
    return offices, reporting


def parse_office(payload, office: dict, reporting: Reporting) -> list[Contest]:
    kind = _OFFICE_TYPES.get(office["OfficeCode"]) or names.office_type(office["OfficeName"])
    contests = []
    # {"Representative in Congress": [{"1st Congressional District$$2$$": [{"District", "Candidates", ...}], ...}]}
    for office_name, groups in (_decode(payload).get("Election") or {}).items():
        for group in groups if isinstance(groups, list) else [groups]:
            for key, entries in group.items():
                for entry in entries:
                    district_name = entry.get("District") or key.split("$$")[0]
                    district = names.district(district_name) if kind not in ("governor", "lt_governor") else None
                    contests.append(Contest(
                        source="pa", contest_id=f"{office['OfficeCode']}/{entry.get('DistrictId') or district_name}",
                        state="PA", title=f"{office_name} {district_name}".strip(), office_type=kind,
                        district=district, jurisdiction="Pennsylvania", reporting=reporting,
                        choices=[Choice(c["CandidateName"].title(), names.to_int(c.get("Votes")),
                                        names.party(c.get("PartyName")), names.to_float(c.get("Percentage")))
                                 for c in entry.get("Candidates") or []]))
    return contests


class Pennsylvania(Source):
    id = "pa"
    state = "PA"
    title = "PA Department of State election returns API"
    platform = "PA ElectionReturn API"
    tiers = frozenset({1, 2})

    def pull(self, fetch):
        election_id, kind, active = find_election(
            fetch.get(API + "GetAllElections", params={"methodName": "GetAllElections"}))
        params = {"electionid": election_id, "electiontype": kind, "isactive": active}
        offices, reporting = parse_offices(fetch.get(
            API + "GetOfficeNames", params={"countyName": "", "methodName": "GetOfficeNames", **params}))
        if not offices:
            raise NotPublished("no offices listed yet")
        contests = []
        for office in offices:
            payload = fetch.get(API + "GetOfficeData", params={
                "officeId": office["OfficeID"], "methodName": "GetOfficeDetails", **params})
            contests += parse_office(payload, office, reporting)
        return contests


SOURCES = [Pennsylvania()]
