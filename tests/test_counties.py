"""Phase 3 county sources and county-aware matching."""
import gzip

from conftest import FIXTURES, FakeFetch
from elex import match
from elex.counties import ca, ny
from elex.model import Choice, Contest
from elex.platforms import livevoterturnout


def test_los_angeles():
    routes = {"GetMenuElections": "ca_la/menu_2026.json", "GetElectionData": "ca_la/election_4348.json"}
    contests = ca.LosAngeles().pull(FakeFetch(routes))
    mayor = next(c for c in contests if c.title == "LOS ANGELES CITY GENERAL MUNICIPAL ELECTION Mayor")
    assert mayor.office_type == "local" and mayor.scope == "complete"
    assert "NITHYA RAMAN" in [ch.name for ch in mayor.choices]
    governor = next(c for c in contests if c.title == "GOVERNOR")
    assert governor.scope == "partial"
    assert any(c.vote_for == 3 for c in contests)  # "Vote for no more than three"


def test_orange_county_live_voter_turnout():
    page = gzip.decompress((FIXTURES / "ca_orange/index_24.html.gz").read_bytes()).decode("utf-8", "replace")
    contests = livevoterturnout.parse(page, source_id="ca.orange", state="CA", jurisdiction="Orange County")
    irvine = next(c for c in contests if c.title == "CITY OF IRVINE Member, City Council District 1")
    assert [ch.name for ch in irvine.choices] == ["MELINDA LIU", "JOHN PARK", "SUKHEE KANG"]
    assert irvine.office_type == "local" and irvine.district == "1"
    props = [c for c in contests if c.title.upper().startswith("PROPOSITION")]
    assert props and all(c.scope == "partial" for c in props)


def test_local_races_only_match_their_own_county():
    la = [Contest(source="ca.los_angeles", contest_id="1", state="CA", jurisdiction="Los Angeles County",
                  title="CITY OF SAN GABRIEL City Clerk", office_type="local", choices=[Choice('THU "JULIE" NGUYEN')])]
    row = {"id": 1, "name": "Michael Nguyen", "office": "San Francisco Board of Supervisors, District 8",
           "office_category": "Local Office", "state_code": "CA", "county": "San Francisco", "position": ""}
    assert match.match_one(row, la).status == "unmatched"
    row = {**row, "county": "Los Angeles", "name": "Julie Nguyen", "office": "San Gabriel City Clerk"}
    assert match.match_one(row, la).status == "auto"


def test_unmatched_local_race_without_a_county_source_is_no_source():
    rows = [{"id": 1, "name": "Someone", "office": "Antioch City Council", "office_category": "Local Office",
             "state_code": "CA", "county": "Contra Costa", "key": "k1", "nov3_ballot": "expected"},
            {"id": 2, "name": "Other", "office": "Burbank City Council", "office_category": "Local Office",
             "state_code": "CA", "county": "Los Angeles", "key": "k2", "nov3_ballot": "expected"}]
    contests = [Contest(source="ca", contest_id="x", state="CA", title="Governor", office_type="governor",
                        choices=[Choice("A")])]
    out = match.match_all(rows, contests, {}, local_states=set(), statewide_states={"CA"},
                          local_counties={("CA", "Los Angeles")})
    assert [r["status"] for r in out] == ["no_source", "unmatched"]


def test_nyc_combines_party_lines_and_marks_city_share_partial():
    senate = ny.parse((FIXTURES / "nyc/state_senate.html").read_text(encoding="latin-1"))
    assert len(senate) == 28
    sd10 = next(c for c in senate if c.district == "10")
    assert sd10.office_type == "state_senate" and sd10.scope == "complete"
    sanders = sd10.choices[0]
    assert sanders.name == "James Sanders Jr." and sanders.party == "DEM" and set(sanders.party_lines) == {"DEM", "WFP"}
    assert {c.district for c in senate if c.scope == "partial"} == {"34", "36"}  # cross into Westchester/Nassau
    governor, = ny.parse((FIXTURES / "nyc/governor.html").read_text(encoding="latin-1"))
    assert governor.office_type == "governor" and governor.scope == "partial"
    assert governor.feed_updated_at == "2026-11-03T19:00:00-05:00"


def test_county_source_doesnt_match_other_districts():
    # NYC covers some Assembly districts; a Robert Carroll in AD 44 isn't WFP's Patrick Carroll in AD 96.
    nyc = [Contest(source="ny.nyc", contest_id="1", state="NY", jurisdiction="New York City",
                   title="Member of the Assembly 44th Assembly District", office_type="state_house", district="44",
                   choices=[Choice("Robert C. Carroll")])]
    row = {"id": 1, "name": "Patrick Carroll", "office": "State Assembly, District 96",
           "office_category": "State House", "state_code": "NY", "county": "", "position": ""}
    assert match.match_one(row, nyc).status == "unmatched"
    row = {**row, "name": "Robert Carroll", "office": "State Assembly, District 44"}
    assert match.match_one(row, nyc).status == "auto"


def test_resultscaster_sums_groups_and_lines():
    from elex.platforms import resultscaster
    shell = {"groups": ["Election Day", "Early Voting"], "contests": [
        {"contestAltTallyKey": "20", "title": "County Clerk", "voteFor": 1, "choices": [
            {"choiceAltTallyKey": "1", "name": "Steven G. Meyer",
             "affiliations": [{"altAffiliationKey": "a", "abbreviation": "DEM"},
                              {"altAffiliationKey": "b", "abbreviation": "WOR"}]},
            {"choiceAltTallyKey": "2", "name": "Write-in", "affiliations": [{"altAffiliationKey": "c"}]}]},
        {"contestAltTallyKey": "7", "title": "State Senator 61st", "voteFor": 1, "choices": []}]}

    def group(dem, wor, progress):
        lines = [{"key": "a", "votes": dem}, {"key": "b", "votes": wor}]
        return {"election": {"contests": [{"key": "20", "progress": progress, "progressTotal": 652,
                                           "choices": [{"key": "1", "votes": dem + wor, "affiliations": lines}]}]}}
    clerk, senate = resultscaster.parse(shell, {"Election Day": group(100, 20, 300), "Early Voting": group(50, 5, 0)},
                                        source_id="ny.erie", state="NY", county="Erie")
    meyer, = clerk.choices  # the write-in line is dropped
    assert meyer.votes == 175 and meyer.party_lines == {"DEM": 150, "WFP": 25} and meyer.party == "DEM"
    assert clerk.reporting.units_reporting == 300 and clerk.scope == "complete"
    assert senate.scope == "partial" and senate.jurisdiction == "Erie County"


def test_legislature_and_legislator_are_the_same_office():
    erie = [Contest(source="ny.erie", contest_id="21", state="NY", jurisdiction="Erie County",
                    title="County Legislator 1st", office_type="local", district="1",
                    choices=[Choice("Lawrence J. Dupre")])]
    row = {"id": 1, "name": "Lawrence Dupre", "office": "Erie County Legislature, District 1",
           "office_category": "Local Office", "state_code": "NY", "county": "Erie", "position": ""}
    assert match.match_one(row, erie).status == "auto"


def test_wisconsin_counties_keep_only_whole_districts_complete():
    from elex.counties import wi
    dane = wi.parse_dane({"LastPublished": "2026-11-03T21:48:02", "Races": [
        {"RaceName": "Representative to the Assembly District 76", "RaceNumber": "0017", "TotalPrecincts": 40,
         "PrecinctsReported": 36, "Candidates": [
             {"Number": 1, "Name": "REP Nina Chat", "Votes": 20, "PartyCode": "REP"},
             {"Number": 2, "Name": "DEM Dina Nina Martinez-Rutherford", "Votes": 80, "PartyCode": "DEM"}]},
        {"RaceName": "State Senator District 17", "RaceNumber": "0009", "Candidates": []},
        {"RaceName": "State Referendum 1 (Partial veto)", "RaceNumber": "0026", "Candidates": [
            {"Number": 1, "Name": "YES", "Votes": 3}, {"Number": 2, "Name": "NO", "Votes": 7}]}]},
        wi.Dane.whole_districts)
    ad76, sd17, question = dane
    assert ad76.scope == "complete" and ad76.choices[1].name == "Dina Nina Martinez-Rutherford"
    assert ad76.reporting.pct == 90.0 and sd17.scope == "partial"
    assert question.office_type == "measure" and question.scope == "partial"
    page = ('Last updated:&nbsp;11/3/2026 9:24:41 PM <div class="contestBox"><h1>Representative to the Assembly '
            'District 64<br /></h1><h2>(Vote for 1)</h2><td class="candtd">&nbsp;DEM Tip McGuire</td><td><div '
            'style="z-index: 1">9485 (58.49%) </div></td></div>')
    ad64, = wi.parse_kenosha(page, wi.Kenosha.whole_districts)
    assert ad64.scope == "complete" and (ad64.choices[0].name, ad64.choices[0].votes) == ("Tip McGuire", 9485)
    assert ad64.feed_updated_at == "2026-11-03T21:24:41"
