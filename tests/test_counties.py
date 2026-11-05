"""Phase 3 county sources and county-aware matching."""
import gzip

import pytest

from conftest import FIXTURES, FakeFetch
from elex import match
from elex.counties import ca, ny
from elex.model import Choice, Contest
from elex.platforms import enhanced_voting, livevoterturnout
from elex.source import NotPublished


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


def test_wayne_totalvote_titles_candidates_and_whole_districts():
    from elex.counties import mi

    def contest(title, precincts, *cands):
        rows = "".join(f'<div class="col display-results-box-d"><h1> {n} </h1><h2 class="{p}">x</h2></div>'
                       f'<div class="col display-results-box-f"><h1>{v}</h1></div>' for n, p, v in cands)
        return f'<h1>{title} - <br>VOTE FOR ONE (1)</h1><div>Precincts Reported: {precincts}</div>{rows}'
    page = ("Results Last Updated: 11/3/2026 11:06:34 PM EST"
            + contest("Representative in Congress District 12", "0 / 304", ("Rashida Tlaib", "DEM", "9,015"))
            + contest("Representative in Congress District 13", "3 / 377", ("Donavan McKinney", "DEM", "20,831"),
                      ("T.P. Nykoriak", "REP", "6,053")))
    cd12, cd13 = mi.parse_totalvote(page, source_id="mi.wayne", county="Wayne", whole=mi.Wayne.whole_districts)
    assert cd12.title == "Representative in Congress District 12" and cd12.scope == "partial"  # Southfield
    assert cd13.scope == "complete" and cd13.reporting.units_total == 377
    assert [(c.name, c.votes, c.party) for c in cd13.choices] == [("Donavan McKinney", 20831, "DEM"),
                                                                   ("T.P. Nykoriak", 6053, "REP")]
    assert cd13.feed_updated_at == "2026-11-03T23:06:34-05:00"


def test_washtenaw_summary_table():
    from elex.counties import mi

    def race(title, *rows):
        cells = "".join(f'<tr><td align=left class="bb1 bold">&nbsp;&nbsp;{n}</td><td class="bb">1</td>'
                        f'<td class="bb">1</td><td class="bb">1</td><td class="bb">{t}</td><td>x%</td></tr>'
                        for n, t in rows)
        return f'<td class="headertr" colspan="4">{title}</td>{cells}'
    page = ("This report created: Tuesday, Nov 03, 2026 10:46:41 PM Precincts Total: | 112 | Precincts Fully "
            "Counted: | 36 |" + race("Mayor City of Ann Arbor", ("Yousef Rabhi", "37914"),
                                     ("Unassigned write-ins", "1170"))
            + race("State Rep 23rd District", ("Jason Morgan", "14175")))
    mayor, hd23 = mi.parse_washtenaw(page, whole=frozenset())
    assert [(c.name, c.votes) for c in mayor.choices] == [("Yousef Rabhi", 37914)]  # write-ins dropped
    assert mayor.scope == "complete" and hd23.scope == "partial"  # HD-23 also has Wayne precincts
    assert mayor.reporting.pct is None and mayor.reporting.text == "Countywide, 36 of 112 precincts fully counted"


class _Pages:
    """A fetcher that serves inline text by URL fragment."""

    def __init__(self, pages: dict):
        self.pages = pages

    def get(self, url, *, params=None, expect="json"):
        for fragment, body in self.pages.items():
            if fragment in url:
                return body.encode() if expect == "bytes" else body
        raise AssertionError(url)


def _lvt_race(race, title, *candidates):
    """One contest in Live Voter Turnout's markup, without a contest group (San Diego's page)."""
    rows = "".join(f'<td data-race="{race}" data-contestant="{i}" data-candidate="true"><span>{name}</span></td>'
                   f'<td data-race="{race}" data-contestant="{i}" data-votes="true">{votes}</td>'
                   for i, (name, votes) in enumerate(candidates))
    return f'<span id="raceHeading_{race}" class="sr-only">Contest: {title}, VOTE FOR 1</span>{rows}'


def test_live_voter_turnout_page_without_groups():
    page = '<h1 class="election-title" tabindex="0">Gubernatorial General Election</h1>' + "".join([
        _lvt_race(1, "GOVERNOR", ("XAVIER BECERRA (DEM)", "100"), ("STEVE HILTON (REP)", "80")),
        _lvt_race(2, "MEMBER OF THE STATE ASSEMBLY 79TH DISTRICT", ("A (DEM)", "5")),
        _lvt_race(3, "CITY OF CARLSBAD TREASURER", ("B", "7")),
        _lvt_race(4, "PROP 1 - HOUSING BONDS", ("YES", "3"), ("NO", "2")),
        _lvt_race(5, "CITY OF OCEANSIDE - MEASURE R - Majority Required", ("YES", "3"), ("NO", "2")),
        _lvt_race(6, "RETAIN COURT OF APPEAL AJ TRUC T. DO", ("YES", "3"), ("NO", "2")),
    ]) + "<p>Last updated 11/4/2026 2:51:51 AM</p>"
    source = livevoterturnout.LiveVoterTurnoutSource("ca.san_diego", "CA", "San Diego", "https://sdvote.com/results",
                                                     "Gubernatorial General Election")
    governor, assembly, treasurer, prop, measure, court = source.pull(_Pages({"sdvote.com": page}))
    assert [(ch.name, ch.party) for ch in governor.choices] == [("XAVIER BECERRA", "DEM"), ("STEVE HILTON", "REP")]
    assert (governor.scope, assembly.scope, prop.scope, court.scope) == ("partial",) * 4
    assert (treasurer.office_type, treasurer.scope) == ("local", "complete")
    assert measure.scope == "complete"
    stale = page.replace("11/4/2026", "6/3/2026")
    with pytest.raises(NotPublished):
        source.pull(_Pages({"sdvote.com": stale}))


def test_enhanced_voting_strips_fusion_line_prefix():
    payload = {"ballotItems": [{"id": "1", "name": "Supervisor Penfield", "summaryResults": {"ballotOptions": [
        {"name": "Kevin Berry", "voteCount": 100, "party": "DEM"},
        {"name": "WOR Kevin Berry", "voteCount": 12, "party": "WOR"}]}}]}
    contest, = enhanced_voting.parse(payload, source_id="ny.monroe", state="NY", jurisdiction="Monroe County")
    assert [(ch.name, ch.votes) for ch in contest.choices] == [("Kevin Berry", 112)]


def test_chautauqua_xml():
    xml = """<election timestamp="11/3/2026 10:03:35 PM" date="Tuesday, November 3, 2026">
      <areatypes>
        <admindivision name="State"><area id="1" name="New York State"/></admindivision>
        <admindivision name="Town"><area id="23" name="Town of Kiantone"/></admindivision>
      </areatypes>
      <parties><party id="1" abbrev="DEM"/><party id="2" abbrev="REP"/></parties>
      <offices>
        <office><contests><contest id="135" name="Member of Assembly District 150" areaid="1"><choices>
          <choice id="10" name="Thomas A. Carle" isw="False"><aff id="1"/></choice>
          <choice id="11" name="Write-in" isw="True"/></choices></contest></contests></office>
        <office><contests><contest id="73" name="Town Clerk" areaid="23"><choices>
          <choice id="20" name="Mary Cook" isw="False"><aff id="2"/></choice>
          <choice id="21" name="Jennifer A. Schmitt" isw="False"/></choices></contest></contests></office>
      </offices>
      <simpleresults><ch id="10" v="900"/><ch id="11" v="0"/><ch id="20" v="300"/><ch id="21" v="200"/></simpleresults>
      <contestoverview><co c="135" n="1"/><co c="73" n="1"/></contestoverview>
      <progress closed="91" total="91"/>
    </election>"""
    assembly, clerk = ny.parse_chautauqua(xml)
    assert (assembly.office_type, assembly.district, assembly.scope) == ("state_house", "150", "partial")
    assert [ch.name for ch in assembly.choices] == ["Thomas A. Carle"]  # empty write-in dropped
    assert (clerk.title, clerk.office_type, clerk.scope) == ("Town Clerk, Town of Kiantone", "local", "complete")
    assert clerk.choices[0].party == "REP" and clerk.reporting.text == "Countywide, 91 of 91 poll sites reported"


def test_nyc_keeps_the_bolded_leading_row():
    row = ('<tr><td{b}>{n}</td><td>&nbsp;</td><td{b}>{name}&nbsp;</td><td{b}>Democratic&nbsp;</td>'
           '<td align="right"{b}>&nbsp;{votes}</td><td align="right"{b}>&nbsp;50%</td>')
    page = ('<th>Member of the Assembly 50th Assembly District<div style="x">(Vote for one)</div></th>'
            + row.format(b=' style="font-weight: bold"', n=1, name="Emily Gallagher", votes=22686)
            + row.format(b=" ", n=2, name="WRITE-IN", votes=619))
    contest, = ny.parse(page)
    assert [(ch.name, ch.votes) for ch in contest.choices] == [("Emily Gallagher", 22686), ("WRITE-IN", 619)]


def test_county_shares_summed_into_districts():
    from elex import combine
    from elex.source import Source

    def county(id_, name):
        s = Source()
        s.id, s.state, s.level, s.county = id_, "NY", "county", name
        return s

    def share(source, district, *choices):
        return Contest(source=source, contest_id=district, state="NY", title=f"State Senator {district}th District",
                       office_type="state_senate", district=district, scope="partial",
                       choices=[Choice(n, v) for n, v in choices])
    sources = [county("ny.a", "Alpha"), county("ny.b", "Beta")]
    latest = {
        "ny.a": {"status": "ok", "contests": [share("ny.a", "40", ("Pete Harckham", 100), ("Rival", 80)),
                                              share("ny.a", "41", ("X", 1))]},
        "ny.b": {"status": "ok", "contests": [share("ny.b", "40", ("Peter Harckham", 20), ("Rival", 30))]}}
    mapping = {"state_senate": {"40": {"Alpha": 10, "Beta": 5}, "41": {"Alpha": 10, "Beta": 1},
                                "42": {"Alpha": 3, "Gamma": 9}}}
    contests, skipped = combine.build(latest, sources, mapping)
    by_district = {c.district: c for c in contests}
    sd40 = by_district["40"]
    assert [(ch.name, ch.votes) for ch in sd40.choices] == [("Peter Harckham", 120), ("Rival", 110)]
    assert sd40.reporting.text == "Summed from Alpha and Beta county results"
    assert [(ch.name, ch.votes) for ch in by_district["41"].choices] == [("X", 1)]  # Beta lists no SD-41 voters
    assert "42" not in by_district and any("Gamma" in line for line in skipped)  # Gamma has no source
    latest["ny.b"]["status"] = "error"  # a timeout keeps the county's last good results
    assert {c.district for c in combine.build(latest, sources, mapping)[0]} == {"40", "41"}
    latest["ny.b"]["status"] = "not_published"
    assert {c.district for c in combine.build(latest, sources, mapping)[0]} == set()


def test_summary_pdf_combines_party_lines():
    from elex.platforms import summary_pdf
    text = "\n".join([
        "Albany County Election Night Unofficial Results", "2026 General Election 100% Precincts Reporting",
        "November 3, 2026", "Statistics TOTAL Election Early Absentee Affidavit",
        "Ballots Cast - Total 116,201 68,471 41,462 6,268 0",
        "Member of Assembly District 107", "Vote For 1", "TOTAL VOTE % Election Early Absentee Affidavit",
        "Day Voting", "DEM Chloe E. Pierce 10,199 60.52% 3,896 5,695 608 0",
        "REP Scott H. Bendett 4,418 26.21% 2,755 1,517 146 0", "WFP Chloe E. Pierce 1,222 7.25% 520 645 57 0",
        "Write-In Totals 22 0.13% 12 10 0 0", "Contest Totals 16,853 100.00% 7,762 8,118 833 0",
        "Election Summary - 11/04/2026 1:29 AM Page 2 of 10",
        "County Legislature County Legislative District 6", "Vote For 1",
        "DEM Racquel Saddler 1,293 98.00% 1 1 1 0", "Contest Totals 1,320 100.00% 1 1 1 0"])
    assembly, legislature = summary_pdf.parse(text, source_id="ny.albany", state="NY", county="Albany")
    assert (assembly.office_type, assembly.district, assembly.scope) == ("state_house", "107", "partial")
    pierce = assembly.choices[0]
    assert (pierce.name, pierce.votes, pierce.party_lines) == ("Chloe E. Pierce", 11421, {"DEM": 10199, "WFP": 1222})
    assert assembly.feed_updated_at == "2026-11-04T01:29:00-05:00"
    assert (legislature.office_type, legislature.scope) == ("local", "complete")  # a county's, not the state's


def test_statement_of_votes_layout():
    from elex.platforms import summary_pdf
    header = ["Statement of Votes Cast by Geography Page: 3 of 11",
              "Saratoga County, 2026 General Election, Nov 03, 2026 2026-11-03",
              "All Election Districts, All Districts, All Counter Groups, All ScanStations 23:54:19",
              "Total Ballots Cast: 101777", "204 precincts reported out of 204 total", "Choice Votes"]
    text = "\n".join(header + [
        "113th Assembly District (Vote for 1)", "43779 ballots (21 over voted ballots)",
        "94 precincts reported out of 94 total", "Thomas J. Kenny 1046", "Working Families 778", "No Kings 268",
        "Carrie Woerner 25030", *header, "Write-in 25", "Total 26101", "Undervotes 483",
        "Senator 44th District (Vote for 1)", "204 precincts reported out of 204 total",
        "Sarah F. Rogerson 49124", "Democratic 44952", "Working Families 4172", "Total 49124"])
    assembly, senate = summary_pdf.parse_statement(text, source_id="ny.saratoga", state="NY", county="Saratoga")
    assert [(c.name, c.votes) for c in assembly.choices] == [("Thomas J. Kenny", 1046), ("Carrie Woerner", 25030)]
    assert assembly.choices[0].party_lines == {"WFP": 778, "NO KINGS": 268}
    assert (assembly.reporting.units_reporting, assembly.reporting.units_total) == (94, 94)
    assert (senate.office_type, senate.district) == ("state_senate", "44")
    assert senate.choices[0].party_lines == {"DEM": 44952, "WFP": 4172}


def test_nassau_and_schenectady_text():
    nassau = ny.parse_nassau(
        "Unofficial Results November 3, 2026 General Election 1042 precincts reported out of 1083 total "
        "2026-11-03 23:55:59 ChoiceVotes Vote % All Precincts State Senator District 6 (Vote for 1) "
        "Siela A. Bynoe 66198 67.45% Democratic63702 Working Families 2496 Matthew J. Capp 31920 32.52% "
        "Republican29207 Conservative2713 Write-in40 0.04% Total98158100.00%")
    sd6, = nassau
    assert [(c.name, c.votes, c.party) for c in sd6.choices] == [("Siela A. Bynoe", 66198, "DEM"),
                                                                 ("Matthew J. Capp", 31920, "REP")]
    assert sd6.choices[0].party_lines == {"DEM": 63702, "WFP": 2496} and sd6.scope == "partial"
    lines = ["UNOFFICIAL RESULTS", "November 3, 2026", "Election Day Precincts Reporting", "101 of 102", "TOTAL",
             "Vote For 1", "Member of Assembly District 110", "DEM Phillip G. Steck", "8,415",
             "REP Frank A. Mauriello", "3,556", "WOR Phillip G. Steck", "901", "Write-In Totals", "17", "TOTAL"]
    ad110, = ny.parse_schenectady(lines)
    assert [(c.name, c.votes) for c in ad110.choices] == [("Phillip G. Steck", 9316), ("Frank A. Mauriello", 3556)]
    assert ad110.reporting.text == "Countywide, 101 of 102 precincts reporting"


def test_nts_vic_combines_party_lines():
    from elex.platforms import nts_vic

    def row(cid, name, party, votes):
        return {"choiceId": cid, "choiceName": name, "ppAbb": party, "totalVot": votes}
    details = {"textDate": "11/03/2026 00:00:00", "updatedDate": "2026-11-03T23:33:50.54",
               "electionDayMessage": "Fully Reported", "absenteeMessage": "Partially Reported"}
    result = {"oldContest": [
        {"contestId": 7, "name": "State Senator 62nd District - SD 62", "choices": [
            row(1, "Thomas E. Arida", "DEM", 27590), row(2, "Robert G. Ortt", "REP", 38808),
            row(1, "Thomas E. Arida", "WOR", 2632), row(9, "Write-in", None, 0)]},
        {"contestId": 13, "name": "County Legislator District 1 - LD 1", "choices": [row(3, "Irene M. Myers", "REP", 5)]}]}
    senate, legislator = nts_vic.parse(details, result, source_id="ny.niagara", state="NY", county="Niagara")
    assert (senate.title, senate.office_type, senate.district, senate.scope) == (
        "State Senator 62nd District", "state_senate", "62", "partial")
    arida = senate.choices[0]
    assert (arida.votes, arida.party, arida.party_lines) == (30222, "DEM", {"DEM": 27590, "WFP": 2632})
    assert len(senate.choices) == 2 and legislator.scope == "complete"
    assert senate.reporting.text == "Countywide: election day fully reported, absentees partially reported"
