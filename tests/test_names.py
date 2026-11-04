from elex import names


def test_fold_and_surname():
    assert names.fold("Sarah Rascón") == "sarah rascon"
    assert names.surname("Luc Jasmin III") == "jasmin"
    assert names.surname('Nicholas "Nick" Schultz') == "schultz"
    assert names.surname("AnnaJane (AJ) Yolken") == "yolken"
    assert names.surname("Lola Smallwood-Cuevas") == "cuevas"
    assert names.first_name("Rev. Rodney Sadler") == "rodney"


def test_office_type():
    cases = {
        "U.S. House of Representatives, District 12": "federal_house",
        "Representative in Congress District 1": "federal_house",
        "Senator in Congress": "federal_senate",
        "Member of Assembly 88th District": "state_house",  # Westchester drops NYC's "the"
        "U.S. Senate": "federal_senate",
        "NC HOUSE OF REPRESENTATIVES DISTRICT 030": "state_house",
        "Sate Assembly, District 47": "state_house",
        "Representative in General Assembly District 7": "state_house",
        "Senator in General Assembly District 8": "state_senate",
        "Legislative District 36 - State Senator": "state_senate",
        "Governor and Lieutenant Governor": "governor",
        "Lieutenant Governor": "lt_governor",
        "State Insurance Commissioner": "insurance_commissioner",
        "Board of Equalization, District 2": "board_of_equalization",
        "NC SUPREME COURT ASSOCIATE JUSTICE SEAT 01": "judicial",
        "Providence City Council, Ward 5": "local",
    }
    for text, expected in cases.items():
        assert names.office_type(text) == expected, text


def test_district():
    assert names.district("State Senate, Distrcit 6") == "6"
    assert names.district("Washington State House, District 37, Position 1") == "37"
    assert names.district("NC HOUSE OF REPRESENTATIVES DISTRICT 030") == "30"
    assert names.district("1st Congressional District") == "1"
    assert names.district("Representative in the General Assembly 201st Legislative District") == "201"
    assert names.district("Governor") is None


def test_measure_id_and_yes_no():
    assert names.measure_id("Prop – 1: Invest in Affordable Homes") == "1"
    assert names.measure_id("Prop 39: Reject Voter Suppression") == "39"
    assert names.measure_id("Longmont Amendment 3C") == "3c"
    assert names.measure_id("Constitutional Amendment A") == "a"
    assert names.yes_no("FOR") == "Yes"
    assert names.yes_no("AGAINST") == "No"
