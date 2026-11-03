"""Matcher cases found while building against the real contest lists."""
from elex import match
from elex.model import Choice, Contest


def row(name, office, category, state="CA", position="Endorsed", nov3="expected"):
    return {"id": 1, "name": name, "office": office, "office_category": category, "state_code": state,
            "position": position, "key": f"{state}|{name}|{office}", "nov3_ballot": nov3, "nov3_note": ""}


def contest(title, kind, district, *choices, state="CA", source="ca", cid=None):
    return Contest(source=source, contest_id=cid or title, state=state, title=title, office_type=kind,
                   district=district, choices=[Choice(c) for c in choices])


CA = [
    contest("State Senate District 2", "state_senate", "2", "Damon Connolly", "Tief Gibbs"),
    contest("State Senate District 12", "state_senate", "12", "Shannon Grove"),
    contest("State Senate District 6", "state_senate", "6", "Sean Frame", "Roger Niello"),
    contest("State Senate District 26", "state_senate", "26", "Sarah Rascon"),
    contest("State Assembly District 44", "state_house", "44", 'Nicholas "Nick" Schultz'),
    contest("Proposition 39", "measure", "39", "Yes", "No"),
]


def test_district_surname_and_typos():
    m = match.match_one(row("Sean Frame", "State Senate, Distrcit 6", "State Senate"), CA)
    assert (m.status, m.choice.name) == ("auto", "Sean Frame")
    assert match.match_one(row("Sarah Rascón", "State Senate, District 26", "State Senate"), CA).status == "auto"
    assert match.match_one(row("Nick Schultz", "Sate Assembly, District 44", "State House"), CA).status == "auto"


def test_wrong_district_needs_review():
    m = match.match_one(row("Damon Connolly", "State Senate, District 12", "State Senate"), CA)
    assert m.status == "needs_review" and m.contest.district == "2"
    assert "district differs" in m.note


def test_measure_uses_position():
    m = match.match_one(row("Prop 39: Reject Voter Suppression", "Ballot Measure", "Ballot Measure",
                            position="No"), CA)
    assert (m.status, m.choice.name) == ("auto", "No")


def test_joint_ticket_matches_lieutenant_governor():
    nm = [contest("Governor and Lieutenant Governor", "governor", None,
                  "DEB HAALAND AND STEPHANIE GARCIA RICHARD", "GREGGORY D HULL AND DAVID M GALLEGOS", state="NM")]
    m = match.match_one(row("Stephanie Garcia Richard", "Lieutenant Governor", "State Executive", state="NM"), nm)
    assert m.status == "auto"


def test_local_needs_first_name_and_office_overlap():
    ri = [contest("Providence: City Council Ward 5", "local", "5", "Christopher L. Woodley", "Jacqueline Goldman",
                  state="RI"),
          contest("Providence: Mayor", "local", None, "David Morales", state="RI"),
          contest("Coventry: Town Council District 1", "local", "1", "Jonathan J. Pascua", state="RI")]
    assert match.match_one(row("David Morales", "Providence Mayor", "Local Office", state="RI"), ri).status == "auto"
    nickname = match.match_one(row("Jackie Goldman", "Providence City Council, Ward 5", "Local Office", state="RI"),
                               ri)
    assert nickname.status == "needs_review" and nickname.choice.name == "Jacqueline Goldman"
    # Same first name in another town's race isn't a match.
    other = match.match_one(row("Jonathan Jacobs", "East Providence City Council, Ward 1", "Local Office",
                                state="RI"), ri)
    assert other.status == "unmatched"


def test_match_all_statuses_and_preserved_rows():
    rows = [row("Damon Connolly", "State Senate, District 12", "State Senate"),
            row("Someone", "Oakland City Council", "Local Office"),
            row("Gone", "State Senate, District 9", "State Senate", nov3="no"),
            row("Rashida Tlaib", "U.S. House of Representatives, District 12", "Federal House", state="MI")]
    previous = {"CA|Damon Connolly|State Senate, District 12": {
        "wfp_id": "1", "state": "CA", "name": "Damon Connolly", "office": "State Senate, District 12",
        "status": "confirmed", "method": "surname_any_district", "source": "ca", "contest_id": "x",
        "contest_title": "State Senate District 2", "choice_id": "Damon Connolly", "choice": "Damon Connolly",
        "note": ""}}
    out = {r["name"]: r for r in match.match_all(rows, CA, previous, local_states=set())}
    assert out["Damon Connolly"]["status"] == "confirmed"
    assert out["Someone"]["status"] == "no_source"
    assert out["Gone"]["status"] == "not_on_ballot"
    assert out["Rashida Tlaib"]["status"] == "no_source"


def test_manual_only_used_when_scrapers_miss():
    manual = [contest("U.S. House District 12", "federal_house", "12", "Rashida Tlaib", "Someone Else",
                      state="MI", source="manual", cid="mi.us-house.12")]
    rows = [row("Rashida Tlaib", "U.S. House of Representatives, District 12", "Federal House", state="MI")]
    out = match.match_all(rows, manual, {})
    assert (out[0]["status"], out[0]["source"]) == ("auto", "manual")
    scraped = [contest("Rep District 12", "federal_house", "12", "Rashida Tlaib", state="MI", source="mi")]
    out = match.match_all(rows, manual + scraped, {})
    assert out[0]["source"] == "mi"
