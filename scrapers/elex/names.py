"""Normalizing shared by sources and the matcher: text folding, office types, districts, measure IDs, surnames.

Sources and the matcher both call office_type() and district(), so a contest title and a WFP office string that
describe the same race land on the same (office_type, district) pair.
"""
import re
import unicodedata

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
TITLES = {"rev", "dr", "hon", "mr", "mrs", "ms"}

# Statewide propositions are numbered ("PROP 1 - ...", "State Proposition 40"); county and city measures are lettered
# ("Measure A", "Proposition 1A"). A county site's numbered proposition is its share of a statewide vote.
STATE_PROP = re.compile(r"(?i)\bprop(osition)?\s+\d+\b")


def fold(text: str) -> str:
    """Lowercase, strip accents and punctuation: 'Rascón' -> 'rascon', 'Smallwood-Cuevas' -> 'smallwood cuevas'."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[’'`]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return fold(text).split()


def surname(name: str) -> str:
    """Last name token, ignoring suffixes and parenthesized/quoted nicknames: 'Luc Jasmin III' -> 'jasmin'."""
    name = re.sub(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”", " ", name)
    toks = [t for t in tokens(name) if t not in SUFFIXES]
    return toks[-1] if toks else ""


def first_name(name: str) -> str:
    name = re.sub(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”", " ", name)
    toks = [t for t in tokens(name) if t not in TITLES]
    return toks[0] if toks else ""


# Ordered: the first pattern that matches the folded text wins. Federal before state, lieutenant before governor.
_OFFICE_PATTERNS = [
    # A county's own legislature ("County Legislature County Legislative District 6", Albany) isn't the state's.
    ("local", r"\bcounty legislat"),
    ("federal_senate", r"\b(u ?s|united states) senat|\bsenator in congress\b|\bus senator\b"),
    ("federal_house", r"\b(u ?s|united states) (house|rep|congress)|\b(in|to) congress\b|\bcongressional\b"
                      r"|\bus house\b"),
    # Joint tickets (NM "Governor and Lieutenant Governor", MD "Governor / Lt. Governor"): both names on one choice.
    ("governor", r"^governor (and )?(lieutenant|lt) governor"),
    ("lt_governor", r"\blieutenant governor\b|\blt governor\b"),
    ("governor", r"\bgovernor\b"),
    ("attorney_general", r"\battorney general\b"),
    ("secretary_of_state", r"\bsecretary of (the )?state\b"),
    ("treasurer", r"\btreasurer\b"),
    ("controller", r"\b(controller|comptroller)\b"),
    ("auditor", r"\bstate auditor\b|\bauditor of state\b"),
    ("insurance_commissioner", r"\binsurance commissioner\b"),
    ("board_of_equalization", r"\bequalization\b"),
    ("public_lands", r"\bpublic lands\b"),
    ("superintendent", r"\bsuperintendent of public instruction\b"),
    ("labor_commissioner", r"\blabor commissioner\b|\bcommissioner of labor\b|\bbureau of labor\b"),
    ("public_service_commission", r"\bpublic service commission\b"),
    ("corporation_commission", r"\bcorporation commission\b"),
    ("state_senate", r"\bstate senat|\bsenator in (the )?general assembly\b|\bnc senate\b|\bsenate district\b"
                     r"|^senate\b|\bstate senator\b"),
    ("state_house", r"\bstate (house|assembly|representative)|\bsate assembly\b|\bgeneral assembly\b"
                    r"|\bhouse of representatives\b|\bassembly district\b|\bhouse district\b|^assembly\b"
                    r"|\blegislature\b|\bstate rep|\bhouse of delegates\b|\bmember of (the )?assembly\b"),
    ("judicial", r"\bcourt\b|\bjudge\b|\bjustice\b|\bjudicial\b"),
]

def office_type(text: str) -> str:
    """Map an office or contest title to the fixed office-type list. Anything unrecognized is 'local'."""
    folded = fold(text)
    for name, pattern in _OFFICE_PATTERNS:
        if re.search(pattern, folded):
            return name
    return "local"


def wfp_office_type(row: dict) -> str:
    """Office type for a WFP endorsement, using its scraped category first and the office text second."""
    category = row["office_category"]
    if category == "Ballot Measure":
        return "measure"
    fixed = {"Federal Senate": "federal_senate", "Federal House": "federal_house",
             "State Senate": "state_senate", "State House": "state_house", "Judicial": "judicial"}
    if category in fixed:
        return fixed[category]
    kind = office_type(row["office"])
    if category == "Local Office" and kind not in ("judicial",):
        return "local"
    if category == "State Executive" and kind == "local":
        return "state_other"  # a statewide office office_type() doesn't know ("Auditor", "Land Commissioner")
    return kind


def district(text: str) -> str | None:
    """District number as a string without leading zeros. Prefers the number after 'district' (tolerating typos
    like 'Distrcit'), so 'District 37, Position 1' is 37; otherwise the last number ('1st Congressional' is 1)."""
    folded = fold(text)
    m = re.search(r"\bdistr\w*\s+(\d+)", folded) or re.search(r"\b(\d+)(?:st|nd|rd|th)?\s+(?:congressional|"
                                                               r"legislative|senatorial|district)\b", folded)
    if m:
        return str(int(m.group(1)))
    nums = re.findall(r"\d+", folded)
    return str(int(nums[-1])) if nums else None


def measure_id(text: str) -> str | None:
    """Measure number or letter: 'Prop – 1: Invest…' -> '1', 'Amendment 3C' -> '3c', 'Question 9' -> '9'."""
    folded = fold(text)
    m = re.search(r"\b(?:prop|proposition|measure|amendment|question|issue|initiative|referendum|bond question|"
                  r"ballot question)\s+(?:no\s+)?([0-9]+[a-z]?|[a-z]{1,2})\b", folded)
    if not m:
        return None
    ident = m.group(1)
    return str(int(ident)) if ident.isdigit() else re.sub(r"^0+(\d)", r"\1", ident)


def yes_no(label: str) -> str:
    """Map a measure's choice label to Yes/No ('FOR', 'Bonds, Yes' -> 'Yes')."""
    folded = fold(label)
    # The first word decides when it's yes or no: Florida's "No for Rejection" also contains "for".
    first = folded.split()[0] if folded.split() else ""
    if first in ("yes", "no"):
        return first.capitalize()
    if re.search(r"\b(yes|for|approve|approved|si)\b", folded):
        return "Yes"
    if re.search(r"\b(no|against|reject|rejected)\b", folded):
        return "No"
    return label.strip()


def party(label: str | None) -> str | None:
    """Short party code: 'Democratic', 'DEMOCRAT', 'Dem' -> 'DEM'."""
    if not label:
        return None
    folded = re.sub(r"\s+party$", "", fold(label))
    table = {"dem": "DEM", "democrat": "DEM", "democratic": "DEM", "rep": "REP", "republican": "REP",
             "lib": "LIB", "libertarian": "LIB", "gre": "GRE", "green": "GRE", "ind": "IND", "independent": "IND",
             "wor": "WFP", "working families": "WFP", "wfp": "WFP", "una": "UNA", "unaffiliated": "UNA",
             "non": None, "nonpartisan": None, "np": None, "write in": "WRITE-IN"}
    return table.get(folded, label.strip().upper()[:12] or None)


def to_int(value) -> int:
    """Votes as an int from '1,234', 1234.0, '' or None."""
    if value in (None, ""):
        return 0
    return int(float(str(value).replace(",", "")))


_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                 "ten": 10}


def vote_for(value) -> int:
    """Seats in a contest from 3, "3", "Vote for 3" or "Vote for no more than three". Defaults to 1."""
    text = fold(str(value or ""))
    m = re.search(r"\d+", text)
    if m:
        return int(m.group())
    return next((n for word, n in _NUMBER_WORDS.items() if re.search(rf"\b{word}\b", text)), 1)


def to_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(str(value).replace(",", "").replace("%", ""))
