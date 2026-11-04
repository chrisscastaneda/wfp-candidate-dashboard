"""Phase 2 parsers: Clarity, Connecticut, Oregon, Ohio, Delaware, Maryland, Florida."""
from datetime import date

import pytest

from conftest import FakeFetch
from elex import config, match
from elex.platforms import clarity
from elex.source import NotPublished
from elex.states import clarity_states, ct, de, fl, md, oh, or_

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


def test_clarity_county_site_labels_contests_with_county(monkeypatch):
    # The matcher's county filter needs "County" in the jurisdiction; a bare "Travis" let Travis County's races
    # match a Tarrant County candidate.
    monkeypatch.setattr(config, "ELECTION_DATE", date(2024, 11, 5))
    routes = {"CO/elections.json": "clarity/co_elections.json",
              "CO/122598/current_ver.txt": "clarity/co_2024_current_ver.txt",
              "CO/122598/367167/json/en/summary.json": "clarity/co_2024_summary.json"}
    source = clarity.ClaritySource("co.x", "CO", "x", "x", "CO", level="county", county="Boulder")
    assert {c.jurisdiction for c in source.pull(FakeFetch(routes))} == {"Boulder County"}


def test_clarity_falls_back_to_known_election_id(monkeypatch):
    # Sonoma, Hudson and others linked their Nov 3 election from their own sites but left elections.json empty.
    monkeypatch.setattr(config, "ELECTION_DATE", date(2024, 11, 5))
    routes = {"CO/elections.json": "clarity/empty_elections.json",
              "CO/122598/current_ver.txt": "clarity/co_2024_current_ver.txt",
              "CO/122598/367167/json/en/summary.json": "clarity/co_2024_summary.json"}
    with pytest.raises(NotPublished):
        clarity.ClaritySource("co", "CO", "x", "x", "CO").pull(FakeFetch(routes))
    contests = clarity.ClaritySource("co", "CO", "x", "x", "CO", eid="122598").pull(FakeFetch(routes))
    assert contests and contests[0].url.endswith("/CO/122598/")


def test_connecticut_combines_fusion_lines():
    routes = {"data/Elections.json": "ct/Elections.json", "108/Version.json": "ct/Version.json",
              "Lookupdata.json": "ct/Lookupdata.json", "stateVotes_Electiondata.json": "ct/stateVotes_Electiondata.json",
              "election_Electiondata.json": "ct/election_Electiondata.json"}
    contests = ct.Connecticut().pull(FakeFetch(routes))
    cd5 = next(c for c in contests if c.office_type == "federal_house" and c.district == "5")
    hayes = next(ch for ch in cd5.choices if ch.name == "Jahana Hayes")
    assert set(hayes.party_lines) == {"DEM", "WFP"}
    # Precincts reporting is statewide only, so a district race gets a labeled count, not a percentage.
    assert cd5.reporting.pct is None
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


def test_florida_sums_counties_and_reads_measures():
    header = "RaceCode\tRaceName\tCountyName\tJuris1num\tJuris2num\tPrecincts\tPrecinctsReporting\t" \
             "CanNameFirst\tCanNameMiddle\tCanNameLast\tPartyCode\tCanVotes"
    rows = ["USS\tUnited States Senator\tAlachua\t   \t \t63\t61\tAngie\t\tNixon\tDEM\t100",
            "USS\tUnited States Senator\tBaker\t   \t \t9\t9\tAngie\t\tNixon\tDEM\t20",
            "USS\tUnited States Senator\tAlachua\t   \t \t63\t61\tAshley\t\tMoody\tREP\t80",
            "USR\tRepresentative in Congress, District 10\tOrange\t010\t \t200\t150\tMaxwell\t\tFrost\tDEM\t5",
            "AMD\tBudget Stabilization Fund\tAlachua\t\t\t63\t61\t \t \tNo for Rejection\tNOP\t7"]
    senate, house, measure = fl.parse("\n".join([header, *rows]))
    nixon = senate.choices[0]
    assert (nixon.name, nixon.votes, nixon.party) == ("Angie Nixon", 120, "DEM")
    assert senate.office_type == "federal_senate" and senate.reporting.units_total == 72
    assert (house.office_type, house.district) == ("federal_house", "10")
    assert measure.office_type == "measure" and measure.choices[0].name == "No"


def test_south_carolina_xlsx():
    import io
    import zipfile
    from elex.states import sc

    strings = ["U.S.  House of Representatives, District  4 (Vote For 1)", "REP William Timmons",
               "DEM Courtney McClain", "Write-In", "County", "Total:"]
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'

    def cell(ref, text=None, number=None):
        return f'<c r="{ref}" t="s"><v>{strings.index(text)}</v></c>' if text else f'<c r="{ref}"><v>{number}</v></c>'
    rows = [cell("A1", "U.S.  House of Representatives, District  4 (Vote For 1)"),
            cell("C2", "REP William Timmons") + cell("J2", "DEM Courtney McClain") + cell("Q2", "Write-In"),
            cell("A3", "County"),
            cell("A4", "Total:") + cell("I4", number=146808) + cell("P4", number=129561) + cell("W4", number=12)]
    sheet = f'<worksheet {ns}><sheetData>' + "".join(f"<row>{r}</row>" for r in rows) + "</sheetData></worksheet>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}>' + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/workbook.xml", f'<workbook {ns}><sheets><sheet name="Table of Contents"/><sheet name="18"/>'
                                      "</sheets></workbook>")
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet {ns}><sheetData/></worksheet>")
        z.writestr("xl/worksheets/sheet2.xml", sheet)
    house, = sc.parse(sc.read_xlsx(buf.getvalue()))
    assert (house.title, house.office_type, house.district) == ("U.S. House of Representatives, District 4",
                                                                 "federal_house", "4")
    assert [(c.name, c.party, c.votes) for c in house.choices] == [("William Timmons", "REP", 146808),
                                                                   ("Courtney McClain", "DEM", 129561)]
    assert sc.snapshot_time("x/2026-11-03-12AM-General-Election-Results.xlsx") == "2026-11-04T00:00:00-05:00"
