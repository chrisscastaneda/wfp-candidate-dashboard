#!/usr/bin/env python3
"""Exploratory: can WFP endorsements be auto-matched to an official feed before any votes are counted?

Pulls California's SoS returns API (already serving Nov 3 contests with zero votes), normalizes each
contest to (office type, district), and matches every California state/federal endorsement and
statewide measure in data/candidates.json by office type + district number + candidate surname.
Prints what matched and what didn't. Not part of the scraper system. Standard library only.

Usage: python3 scrapers/explore/explore_match_ca.py
"""
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

API = "https://api.sos.ca.gov/returns/"
DATA = Path(__file__).resolve().parents[2] / "data" / "candidates.json"

# Feed path -> office type used for matching. District offices return a list of contests.
FEEDS = {
    "us-rep/district/all": "federal_house",
    "state-senate/district/all": "state_senate",
    "state-assembly/district/all": "state_house",
    "board-of-equalization/district/all": "board_of_equalization",
    "insurance-commissioner": "insurance_commissioner",
    "ballot-measures": "measure",
}


def get_json(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "wfp-results-explore/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fold(text):
    """Lowercase, strip accents and punctuation: 'Rascón' -> 'rascon'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()


def district_number(text):
    # Tolerates the site's typos ("Distrcit 6") by taking the last number in the office text.
    nums = re.findall(r"\d+", text)
    return int(nums[-1]) if nums else None


def load_contests():
    contests = []
    for path, office_type in FEEDS.items():
        payload = get_json(path)
        if office_type == "measure":
            for m in payload["ballot-measures"]:
                contests.append({"type": "measure", "district": int(m["Number"]), "title": m["Name"], "choices": ["Yes", "No"]})
            continue
        for race in payload if isinstance(payload, list) else [payload]:
            contests.append({
                "type": office_type,
                "district": district_number(race["raceTitle"].split(" - ")[0]),
                "title": race["raceTitle"],
                "reporting": race.get("Reporting"),
                "choices": [c["Name"] for c in race["candidates"]],
            })
    return contests


def wfp_office_type(row):
    office = row["office"].lower()
    if row["office_category"] == "Ballot Measure":
        return "measure"
    if "equalization" in office:
        return "board_of_equalization"
    if "insurance" in office:
        return "insurance_commissioner"
    return {"Federal House": "federal_house", "State Senate": "state_senate", "State House": "state_house"}.get(row["office_category"])


def match(row, contests):
    office_type = wfp_office_type(row)
    if office_type == "measure":
        number = district_number(row["name"].split(":")[0])
        hits = [c for c in contests if c["type"] == "measure" and c["district"] == number]
        # WFP's stance is in `position` ("Yes"/"No"); the matching choice is that side of the measure.
        return (hits[0], row["position"]) if hits else (None, None)
    district = district_number(row["office"]) if office_type not in ("insurance_commissioner",) else None
    candidates = [c for c in contests if c["type"] == office_type and (district is None or c["district"] == district)]
    surname = fold(row["name"]).split()[-1]
    for contest in candidates:
        for choice in contest["choices"]:
            if surname in fold(choice).split():
                return contest, choice
    # Not in the listed district: look in every contest of that office type. A hit here means the
    # WFP listing has the wrong district (it lists Damon Connolly in SD 12; he's on the SD 2 ballot).
    for contest in contests:
        if contest["type"] == office_type and any(surname in fold(ch).split() for ch in contest["choices"]):
            choice = next(ch for ch in contest["choices"] if surname in fold(ch).split())
            return contest, choice + "  [district differs from WFP listing]"
    return (candidates[0] if candidates else None), None


def main():
    contests = load_contests()
    print(f"Loaded {len(contests)} contests from the CA SoS API\n")
    rows = [r for r in json.load(open(DATA, encoding="utf-8"))["candidates"]
            if r["state"] == "California" and r["office_category"] not in ("Local Office", "Judicial")]
    matched = 0
    for row in rows:
        contest, choice = match(row, contests)
        if contest and choice:
            matched += 1
            print(f"  OK   {row['name'][:40]:40} -> {contest['title'][:55]:55} | {choice}")
        else:
            why = "contest found, candidate not on it" if contest else "no contest"
            print(f"  MISS {row['name'][:40]:40} ({row['office']}): {why}")
    print(f"\nMatched {matched} of {len(rows)} California state/federal endorsements and statewide measures")


if __name__ == "__main__":
    main()
