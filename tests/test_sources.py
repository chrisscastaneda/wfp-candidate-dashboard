"""Parsers against the real Nov 3 contest lists."""
import pytest

from conftest import FIXTURES, FakeFetch
from elex.fetch import Blocked
from elex.platforms import enhanced_voting, results_csv
from elex.source import NotPublished
from elex.states import ca, enhanced_voting_states, nc, pa, results_csv_states

EV = {s.id: s for s in enhanced_voting_states.SOURCES}
CSV = {s.id: s for s in results_csv_states.SOURCES}


def _by_title(contests):
    return {c.title: c for c in contests}


def test_california():
    routes = {f"returns/{p}": f"ca/{p.replace('/', '_')}.json" for p in ca.FEEDS}
    contests = ca.California().pull(FakeFetch(routes))
    assert len(contests) > 150
    sd2 = next(c for c in contests if c.office_type == "state_senate" and c.district == "2")
    assert [ch.name for ch in sd2.choices] == ["Damon Connolly", "Tief Gibbs"]
    assert sd2.reporting.units_total == 912
    prop39 = next(c for c in contests if c.office_type == "measure" and c.district == "39")
    assert [ch.name for ch in prop39.choices] == ["Yes", "No"]


def test_pennsylvania():
    routes = {"GetAllElections": "pa/all_elections.json", "GetOfficeNames": "pa/office_names.json"}
    routes.update({f"officeId={i}": f"pa/office_{i}.json" for i in (3, 11, 12, 13)})  # officeId sorts last
    contests = pa.Pennsylvania().pull(FakeFetch(routes))
    house12 = next(c for c in contests if c.office_type == "federal_house" and c.district == "12")
    assert any("Lee" in ch.name for ch in house12.choices)
    assert len([c for c in contests if c.office_type == "state_house"]) > 150
    assert house12.reporting.units_total == 9066
    # A statewide count isn't a district's share, so district races show it as text, not a percentage.
    assert house12.reporting.pct is None and house12.reporting.text.startswith("Statewide, ")


def test_north_carolina_includes_county_races_once():
    routes = {f"results_{n}.txt": f"nc/results_{n}.json" for n in (0, 1, 32, 60)}
    contests = nc.NorthCarolina().pull(FakeFetch(routes))
    titles = [c.title for c in contests]
    assert "Durham County Sheriff" in titles
    assert len(titles) == len(set(titles))
    nch30 = next(c for c in contests if c.office_type == "state_house" and c.district == "30")
    assert any(ch.name == "Marcia Morey" for ch in nch30.choices)


def test_enhanced_voting_utah_reads_localities_without_duplicates():
    routes = {"jurisdictions/Utah": "ut/jurisdiction.json", "elections/Utah/": "ut/data.json",
              "elections/salt-lake-county-ut/": "ut/salt-lake-county.json",
              "elections/utah-county-ut/": "ut/salt-lake-county.json"}
    contests = EV["ut"].pull(FakeFetch(routes))
    titles = [c.title.lower() for c in contests]
    assert "state house district 21" in titles
    assert titles.count("state house district 23 (multi-county)") == 1
    assert all(not ch.name.startswith("DEM ") for c in contests for ch in c.choices)


def test_enhanced_voting_reporting_counts_localities_not_percent():
    def contest(units, total, precincts=()):
        payload = {"precincts": list(precincts), "ballotItems": [{
            "id": "1", "name": "State House District 58", "reportingStatus": {"reportingUnits": units,
                                                                            "totalUnits": total}}]}
        return enhanced_voting.parse(payload, source_id="ga", state="GA", jurisdiction="Georgia")[0].reporting

    # A state file counts counties: one early-vote batch isn't "100% reporting".
    single = contest(1, 1)
    assert single.pct is None and single.text == "1 of 1 county posted results"
    assert contest(13, 159).text == "13 of 159 counties posted results"
    # A county file counts precincts, which stay a percentage.
    precincts = contest(10, 40, precincts=[{}])
    assert precincts.pct == 25.0 and precincts.text is None


def test_enhanced_voting_rhode_island_strips_party_suffix():
    routes = {"jurisdictions/rhodeisland": "ri/jurisdiction.json", "elections/rhodeisland/": "ri/data.json"}
    contests = _by_title(EV["ri"].pull(FakeFetch(routes)))
    hd7 = contests["Representative in General Assembly District 7"]
    assert "Amy J. Santiago" in [ch.name for ch in hd7.choices]
    assert hd7.office_type == "state_house" and hd7.district == "7"


def test_enhanced_voting_not_published_and_blocked():
    routes = {"jurisdictions/rhodeisland": "ri/jurisdiction.json", "elections/rhodeisland/": "ri/data.json"}
    # An unlisted locality is skipped; the state's own contests still come through.
    contests = enhanced_voting.EnhancedVotingSource("x", "RI", "x", "x", "https://x", "rhodeisland",
                                                    localities=["Nowhere County"]).pull(FakeFetch(routes))
    assert len(contests) == 453
    with pytest.raises(NotPublished):
        EV["ga"].pull(FakeFetch({"jurisdictions/Georgia": "ga/jurisdiction_nov2.json"}))  # Nov 3 not posted yet
    with pytest.raises(Blocked):
        EV["wa"].pull(FakeFetch({"jurisdictions/washington": Blocked("403")}))


def test_results_csv_new_mexico():
    routes = {"type=SW": "nm/SW.csv", "type=STATE": "nm/STATE.csv"}
    contests = CSV["nm"].pull(FakeFetch(routes))
    gov = next(c for c in contests if c.title == "Governor and Lieutenant Governor")
    assert gov.office_type == "governor"
    hd2 = next(c for c in contests if c.office_type == "federal_house" and c.district == "2")
    assert "GABRIEL VASQUEZ" in [ch.name for ch in hd2.choices] and hd2.reporting.units_total == 663
    amendment = next(c for c in contests if c.office_type == "measure" and c.district == "1")
    assert [ch.name for ch in amendment.choices] == ["Yes", "No"]


def test_results_csv_nebraska_reporting_format():
    text = (FIXTURES / "ne/All.csv").read_text(encoding="utf-8-sig")
    contests = results_csv.parse(text, source_id="ne", state="NE", jurisdiction="Nebraska")
    senate = next(c for c in contests if c.office_type == "federal_senate")
    assert senate.reporting.units_total == 1322
