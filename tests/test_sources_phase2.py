"""Phase 2 parsers: Clarity, Connecticut, Oregon, Ohio, Delaware, Maryland."""
from datetime import date

from conftest import FakeFetch
from elex import config, match
from elex.platforms import clarity
from elex.states import clarity_states, ct, de, md, oh, or_

CLARITY = {s.id: s for s in clarity_states.SOURCES}


def test_clarity_county_site_marks_state_contests_partial(monkeypatch):
    summary = __import__("json").loads((__import__("conftest").FIXTURES / "clarity/denton_summary.json").read_text())
    contests = clarity.parse(summary, source_id="tx.denton", state="TX", jurisdiction="Denton",
                             partial_shares=True)
    senate = next(c for c in contests if c.title == "United States Senator")
    assert senate.office_type == "federal_senate" and senate.scope == "partial"
    jp = next(c for c in contests if "Justice of the Peace" in c.title)
    assert jp.scope == "complete"


def test_clarity_state_with_county_sub_elections(monkeypatch):
    monkeypatch.setattr(config, "ELECTION_DATE", date(2024, 11, 5))
    routes = {"CO/elections.json": "clarity/co_elections.json",
              "CO/122598/current_ver.txt": "clarity/co_2024_current_ver.txt",
              "CO/122598/367167/json/en/summary.json": "clarity/co_2024_summary.json",
              "CO/122598/367167/json/en/electionsettings.json": "clarity/co_2024_settings.json",
              "CO/Boulder/122606/355964/json/en/summary.json": "clarity/co_boulder_2024_summary.json"}
    source = clarity.ClaritySource("co", "CO", "Colorado", "Colorado", "CO", counties=["Boulder"])
    contests = source.pull(FakeFetch(routes))
    house1 = next(c for c in contests if c.office_type == "federal_house" and c.district == "1")
    assert "119th United States Congress" in house1.title
    boulder = [c for c in contests if c.jurisdiction == "Boulder County"]
    assert boulder and all(not c.title.startswith("Representative to the") for c in boulder)
    question = next(c for c in boulder if c.title == "City of Boulder Ballot Question 2C")
    assert question.office_type == "measure" and question.district == "2c"
    assert [ch.name for ch in question.choices] == ["Yes", "No"]


def test_connecticut_combines_fusion_lines():
    routes = {"data/Elections.json": "ct/Elections.json", "108/Version.json": "ct/Version.json",
              "Lookupdata.json": "ct/Lookupdata.json", "stateVotes_Electiondata.json": "ct/stateVotes_Electiondata.json",
              "election_Electiondata.json": "ct/election_Electiondata.json"}
    contests = ct.Connecticut().pull(FakeFetch(routes))
    cd5 = next(c for c in contests if c.office_type == "federal_house" and c.district == "5")
    hayes = next(ch for ch in cd5.choices if ch.name == "Jahana Hayes")
    assert set(hayes.party_lines) == {"DEM", "WFP"}
    assert len([c for c in contests if c.office_type == "state_house"]) == 151


def test_oregon_reads_second_house_page_and_strips_suffixes():
    routes = {"type=FED": "or/FED.html", "btnHouse4": "or/HOUSE_31_60.html", "type=HOUSE": "or/HOUSE.html",
              "type=CTYALL": "or/CTY26.html", "type=LMEA": "or/LMEA.html", "type=": "or/FED.html"}
    contests = or_.Oregon().pull(FakeFetch(routes))
    districts = {int(c.district) for c in contests if c.office_type == "state_house"}
    assert districts == set(range(1, 61))
    assert not any(c.title.endswith("All Results") or "view results at" in c.title for c in contests)
    measure = next(c for c in contests if c.title.startswith("26-267"))
    assert measure.office_type == "measure" and measure.district == "26-267"


def test_ohio_sums_counties():
    detail = __import__("json").loads((__import__("conftest").FIXTURES / "oh/detail_oh08.json").read_text())
    contest = oh.parse(detail)
    assert contest.office_type == "federal_house" and contest.district == "8"
    assert contest.reporting.units_total == sum(c["totalPrecincts"] for c in detail["contestList"])
    assert any(ch.name == "Vanessa Enoch" for ch in contest.choices)


def test_delaware_and_maryland():
    rows = __import__("json").loads((__import__("conftest").FIXTURES / "de/statewide.json").read_text())
    contests = {c.title: c for c in de.parse(rows)}
    assert contests["State Representative District 2"].office_type == "state_house"
    assert contests["New Castle County Council District 3"].office_type == "local"
    page = (__import__("conftest").FIXTURES / "md/county_16.html").read_text()
    md_contests = md.parse(page, jurisdiction="Montgomery County", county_page=True, id_prefix="county-16")
    executive = next(c for c in md_contests if c.title == "County Executive")
    assert [ch.name for ch in executive.choices] == ["Will Jawando", "Esther Wells"]
    governor = next(c for c in md_contests if c.office_type == "governor")
    assert governor.scope == "partial"


def test_local_measure_needs_place_name():
    from elex.model import Choice, Contest
    hamilton = [Contest(source="oh.hamilton", contest_id="1", state="OH", jurisdiction="Hamilton County",
                        title="8  PROPOSED TAX LEVY (ADDITIONAL) SYCAMORE COMMUNITY CITY SCHOOL DISTRICT",
                        office_type="measure", district="8", choices=[Choice("Yes"), Choice("No")])]
    row = {"id": 1, "name": "Columbus, OH | Issue 8: Our City, Our Say", "office": "Ballot Measure",
           "office_category": "Ballot Measure", "state_code": "OH", "position": "Yes"}
    assert match.match_one(row, hamilton).status == "unmatched"
