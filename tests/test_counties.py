"""Phase 3 county sources and county-aware matching."""
import gzip

from conftest import FIXTURES, FakeFetch
from elex import match
from elex.counties import ca
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
