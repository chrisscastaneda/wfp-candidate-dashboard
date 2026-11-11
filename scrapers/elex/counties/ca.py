"""California county sources: Los Angeles's results API, Alameda's results page, and the counties on Clarity ENR,
Live Voter Turnout and Enhanced Voting.

The state API (states/ca.py) has no local races; these do. County results include the county's share of state and
federal contests, which are marked partial and ignored by the matcher.

Los Angeles (results.lavote.gov), the JSON its results page uses:
  /ElectionResults/GetMenuElections?year=<y>        -> [{ID, Date, Title}]
  /ElectionResults/GetElectionData?electionID=<id>  -> ContestGroups[] -> Contests[] -> Candidates[] (Name, ID): the
                                                       ballot only; its Votes fields stay 0
  /ElectionResults/GetCounterData?electionID=<id>   -> {TimeStamp, Data: [{ReferenceType: "CAND", ReferenceID: candidate
                                                       ID, Value: votes}, ...contest counters]}: the counts

Alameda (alamedacountyca.gov/rovresults/<n>/, <n> linked from acvote.alamedacountyca.gov) is one server-rendered
page with every contest:
  <h1>General Election - November 03, 2026 ... "Last Updated: Monday, November 09, 2026; 4:59 PM"
  <!-- Start CATEGORY:State -->                     Federal, State, Judicial, School, City, Districts, Measures
  <h4 class="racePanelHeading">Member, City Council, District 4 - Berkeley (RCV)</h4>
  <div class="reported ...">31 of 31 Precincts Partially Reported from Vote Centers (100.00% )</div>
  <div class="votefor ...">Vote for no more than Five (5)</div>
  <TH ... scope="row">Barbara Lee</TH> <TD>119,834</TD> <TD>85.36 %</TD>
Ranked-choice contests (Oakland, Berkeley, San Leandro, Albany) show first choices only; the round-by-round
tabulation is a separate script-driven page, so those contests say "first-choice votes" in their title.

Santa Cruz (www2.santacruzcountyca.gov/ElectionSites/ElectionResults/Results) is also one server-rendered page:
  <h1>California General Election<br />November 3, 2026<br />...  <div class="electionTimeStamp">11/10/2026 4:30 PM
  <div class="card-header" id="NameRace_26"> ... Pajaro Valley Unified ... - Trustee Area 4 (Vote for  1)
  <!-- Candidate Data Loop start --> rows of <div class="elec-num">: name, party, "2057 (69.52%)"
State propositions are titled by number ("40 - Imposes One-time Tax ..."), local measures by letter ("E - Sales Tax").

Santa Barbara (sbcvote.com/Elections/results/<2026nov03>/results-1.htm, linked from countyofsb.org by script) is an
"Election Summary Report" saved from Word. As text, every cell is its own line and long titles and names wrap:
  City of Santa Barbara Member City Council / Dist 4 (Vote for 1) / Precincts / Reported: 12 of 12 (100.00%)
  ... / Candidate / Poll / Mail / Total / XAVIER / BECERRA / 8,837 / 80,721 / 89,558 / 66.21%
then an "Unqualified Write-In" table. A title is the run of text lines before "Precincts"; a choice is the text
lines before its poll, mail and total counts and percentage.
"""
from datetime import datetime
import html
import re

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..platforms.clarity import ClaritySource
from ..platforms.enhanced_voting import EnhancedVotingSource
from ..platforms.hart_verity import SHARE_KINDS as HART_SHARE_KINDS, HartVeritySource
from ..platforms.livevoterturnout import LiveVoterTurnoutSource
from ..source import NotPublished, Source

LA = "https://results.lavote.gov/ElectionResults/"

# Group names whose contests are statewide or district races the state API already reports in full.
_LA_SHARES = {"Governor", "Lieutenant Governor", "Secretary of State", "Controller", "Treasurer", "Attorney General",
              "Insurance Commissioner", "Board of Equalization", "U.S. Representative", "State Senator",
              "Member of the Assembly", "Supreme Court Justices", "Appellate Court Justices",
              "Superintendent Public Inst", "State Measures"}


def parse_la(data: dict, counters: dict | None = None) -> list[Contest]:
    """`counters` is GetCounterData's response; without it every count is GetElectionData's (zero)."""
    votes = {str(c["ReferenceID"]): c["Value"] for c in (counters or {}).get("Data") or []
             if c.get("ReferenceType") == "CAND"}
    stamp = (counters or {}).get("TimeStamp")
    updated = datetime.strptime(stamp, "%m/%d/%Y %I:%M:%S %p").isoformat() + "-08:00" if stamp else None
    contests = []
    for group in data.get("ContestGroups") or []:
        share = group.get("Name") in _LA_SHARES
        for item in group.get("Contests") or []:
            title = re.sub(r"\s+", " ", item.get("Title") or "").strip()
            is_measure = item.get("Type") == "Measure"
            kind = "measure" if is_measure else names.office_type(title)
            if group.get("Name") in ("Cities", "Schools", "Library Districts", "Water Districts",
                                     "Recreation and Park", "Sheriff") and kind not in ("judicial",):
                kind = "local"  # "CITY OF ... Member of the City Council" isn't a state office
            choices = [Choice(names.yes_no(c["Name"]) if is_measure else c["Name"],
                              names.to_int(votes.get(str(c.get("ID")), c.get("Votes"))),
                              names.party(c.get("Party")), choice_id=str(c.get("ID")))
                       for c in item.get("Candidates") or []]
            contest = Contest(
                source="ca.los_angeles", contest_id=str(item["ID"]), state="CA", title=title, office_type=kind,
                district=(names.measure_id(title) or title.split()[-1].lower()) if is_measure
                else names.district(title), jurisdiction="Los Angeles County",
                scope="partial" if share else "complete", vote_for=names.vote_for(item.get("VoteFor")),
                reporting=Reporting(names.to_int(item.get("PrecinctsReporting")) if "PrecinctsReporting" in item
                                    else None, item.get("PrecinctCount") or None), feed_updated_at=updated,
                choices=choices)
            contest.fill_percentages()
            contests.append(contest)
    return contests


class LosAngeles(Source):
    id = "ca.los_angeles"
    state = "CA"
    level = "county"
    county = "Los Angeles"
    title = "Los Angeles County Registrar results"
    site_name = "Los Angeles County Registrar-Recorder"
    url = "https://results.lavote.gov/"
    platform = "LA County results API"
    tiers = frozenset({4})

    def pull(self, fetch):
        listed = fetch.get(LA + "GetMenuElections", params={"year": config.ELECTION_DATE.year}).get("Data") or []
        election = next((e for e in listed if e["Date"][:10] == config.ELECTION_DATE.isoformat()), None)
        if not election:
            raise NotPublished(f"no {config.ELECTION_DATE} election listed")
        data = fetch.get(LA + "GetElectionData", params={"electionID": election["ID"]})["Data"]
        return parse_la(data, fetch.get(LA + "GetCounterData", params={"electionID": election["ID"]}))


ALAMEDA = "https://alamedacountyca.gov/rovresults/"
_ALAMEDA_RACE = re.compile(r'racePanelHeading">(.*?)</h[34]>(.*?)<!-- End panelDtl', re.S)
_ALAMEDA_ROW = re.compile(r'<TH[^>]*scope="row">(.*?)</TH>\s*<TD[^>]*>([\d,]*)</TD>', re.S | re.I)


def parse_alameda(page: str) -> list[Contest]:
    stamp = re.search(r"Last Updated: \w+, (\w+ \d+, \d{4}); (\d+:\d+ [AP]M)", page)
    updated = (datetime.strptime(" ".join(stamp.groups()), "%B %d, %Y %I:%M %p").isoformat() + "-08:00"
               if stamp else None)
    contests = []
    for category, body in re.findall(r"<!-- Start CATEGORY:(.*?) -->(.*?)(?=<!-- Start CATEGORY:|\Z)", page, re.S):
        if category.strip() == "Registration & Turnout":
            continue
        share = category.strip() in ("Federal", "State")
        for heading, detail in _ALAMEDA_RACE.findall(body):
            title = re.sub(r"\s+", " ", heading).strip()
            if title.lower() == "propositions":
                continue  # statewide; the state's API reports them in full
            rcv = "(RCV)" in title
            if rcv:
                title = title.replace("(RCV)", "(RCV, first-choice votes)")
            is_measure = category.strip() == "Measures" or bool(re.match(r"(?i)(bond )?measure\b", title))
            kind = "measure" if is_measure else names.office_type(title)
            done = re.search(r'class="reported[^>]*>\s*([^<]*)', detail)
            text = re.sub(r"\s+", " ", done.group(1)).strip() if done else ""
            vote_for = re.search(r'class="votefor[^>]*>([^<]*)', detail)
            choices = []
            for name, votes in _ALAMEDA_ROW.findall(detail):
                name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", name)).strip()
                if name.lower().startswith("write-in") and not names.to_int(votes):
                    continue
                choices.append(Choice(names.yes_no(name) if is_measure else name, names.to_int(votes),
                                      choice_id=name))
            contest = Contest(
                source="ca.alameda", contest_id=f"{category.strip()}/{title}", state="CA", title=title,
                office_type=kind, district=(names.measure_id(title) or names.fold(title)[:60]) if is_measure
                else names.district(title), jurisdiction="Alameda County",
                scope="partial" if share or re.search(r"(?i)supreme court|court of appeal", title) else "complete",
                vote_for=names.vote_for(vote_for.group(1)) if vote_for else 1,
                reporting=Reporting(as_percent=False, text=text) if text else Reporting(),
                feed_updated_at=updated, choices=choices)
            contest.fill_percentages()
            contests.append(contest)
    return contests


class Alameda(Source):
    id = "ca.alameda"
    state = "CA"
    level = "county"
    county = "Alameda"
    title = "Alameda County Registrar of Voters results"
    site_name = "Alameda County Registrar of Voters"
    url = "https://acvote.alamedacountyca.gov/"
    platform = "Alameda ROV results page"
    tiers = frozenset({4})

    def pull(self, fetch):
        home = fetch.get(self.url + "index", expect="text")
        ids = sorted({int(n) for n in re.findall(r"rovresults/(\d+)", home)}, reverse=True)
        when = config.ELECTION_DATE.strftime("%B %d, %Y")
        for n in ids:
            page = fetch.get(f"{ALAMEDA}{n}/", expect="text")
            heading = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
            if heading and when in heading.group(1):
                contests = parse_alameda(page)
                for contest in contests:
                    contest.url = f"{ALAMEDA}{n}/"
                return contests
        raise NotPublished(f"no results page linked from {self.url} is for {when}")


# Offices a county reports only its share of; the state's API reports them in full.
_SHARE_KINDS = {"federal_senate", "federal_house", "state_senate", "state_house", "governor", "lt_governor",
                "secretary_of_state", "controller", "treasurer", "attorney_general", "insurance_commissioner",
                "superintendent", "board_of_equalization"}
SANTA_CRUZ = "https://www2.santacruzcountyca.gov/ElectionSites/ElectionResults/Results"
_SCZ_CELL = re.compile(r'<div class="elec-num">(.*?)</div>', re.S)


def parse_santa_cruz(page: str) -> list[Contest]:
    stamp = re.search(r'electionTimeStamp">\s*([\d/]+ [\d:]+ [AP]M)', page)
    updated = (datetime.strptime(stamp.group(1), "%m/%d/%Y %I:%M:%S %p").isoformat() + "-08:00"
               if stamp else None)
    contests = []
    for race_id, header, body in re.findall(
            r'<div class="card-header" id="NameRace_(\d+)">(.*?)</a>(.*?)(?=<div class="card-header" id="NameRace_|\Z)',
            page, re.S):
        heading = html.unescape(re.sub(r"<[^>]+>", " ", header))
        m = re.match(r"\s*(.*?)\s*\(Vote for\s+(\d+)\)", heading, re.S)
        if not m:
            continue
        title, vote_for = re.sub(r"\s+", " ", m.group(1)), int(m.group(2))
        rows = re.search(r"Candidate Data Loop start -->(.*?)<!-- Candidate Data Loop End", body, re.S)
        cells = [html.unescape(re.sub(r"\s+", " ", c)).strip() for c in _SCZ_CELL.findall(rows.group(1))] if rows else []
        choices = []
        for name, _party, total in zip(cells[0::3], cells[1::3], cells[2::3]):
            votes = names.to_int(total.split("(")[0])
            if name.lower().startswith("write-in") and not votes:
                continue
            choices.append(Choice(re.sub(r",\s*(jr|sr|ii|iii|iv)\.?$", r" \1", name, flags=re.I), votes, choice_id=name))
        state_prop = re.match(r"\d+ - ", title)
        is_measure = bool(state_prop or re.match(r"[A-Z]{1,2} - ", title))
        if is_measure:
            for c in choices:
                c.name = names.yes_no(c.name)
        kind = "measure" if is_measure else names.office_type(title)
        share = bool(state_prop) or kind in _SHARE_KINDS or bool(re.search(r"(?i)supreme court|appellate", title))
        contest = Contest(
            source="ca.santa_cruz", contest_id=race_id, state="CA", title=title, office_type=kind,
            district=names.measure_id("Measure " + title.split(" - ")[0]) if is_measure else names.district(title),
            jurisdiction="Santa Cruz County", scope="partial" if share else "complete", vote_for=vote_for,
            feed_updated_at=updated, url=SANTA_CRUZ, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class SantaCruz(Source):
    id = "ca.santa_cruz"
    state = "CA"
    level = "county"
    county = "Santa Cruz"
    title = "Santa Cruz County Elections results"
    site_name = "Santa Cruz County Elections"
    url = SANTA_CRUZ
    platform = "Santa Cruz results page"
    tiers = frozenset({4})

    def pull(self, fetch):
        page = fetch.get(self.url, expect="text")
        headings = " ".join(re.findall(r"<h1[^>]*>(.*?)</h1>", page, re.S))
        when = f"{config.ELECTION_DATE:%B} {config.ELECTION_DATE.day}, {config.ELECTION_DATE.year}"
        if when not in headings:
            raise NotPublished(f"{self.url} isn't the {when} election")
        return parse_santa_cruz(page)


_NUMBER = re.compile(r"^[\d,]+$")
_PERCENT = re.compile(r"^[\d.]+%$")


def word_lines(page: str) -> list[str]:
    """A Word-saved HTML report as one line per cell or paragraph."""
    text = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", "", page)
    text = re.sub(r"(?i)</(td|th|tr|p|div|h\d)>|<br[^>]*>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    return [line for line in (re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")) if line]


def parse_santa_barbara(page: str, url: str | None = None) -> list[Contest]:
    lines = word_lines(page)
    contests, pending, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        if line != "Precincts":
            # Counts, percentages and summary lines ("Cards Cast: 273,237") end any title in progress.
            numeric = _NUMBER.match(line) or _PERCENT.match(line) or re.match(r"^[\d,]+ / [\d,]+$", line) \
                or re.match(r"^[A-Za-z ]+: [\d,]+", line)
            pending = [] if numeric else pending + [line]
            i += 1
            continue
        heading = " ".join(pending)
        pending = []
        m = re.match(r"(.*?)\s*\(Vote\s+for\s+(\d+)\)$", heading)
        title, vote_for = (m.group(1), int(m.group(2))) if m else (heading, 1)
        done = re.match(r"Reported: ([\d,]+) of ([\d,]+)", lines[i + 1]) if i + 1 < len(lines) else None
        # Choices start after the "Candidate / Poll / Mail / Total" header.
        j = next((k for k in range(i, min(i + 30, len(lines) - 3)) if lines[k:k + 4] == ["Candidate", "Poll", "Mail", "Total"]),
                 None)
        if j is None:
            i += 1
            continue
        choices, name, k = [], [], j + 4
        while k < len(lines) and lines[k] not in ("Poll", "Precincts"):
            if not _NUMBER.match(lines[k]):
                name.append(lines[k])
                k += 1
                continue
            if k + 3 >= len(lines) or not _PERCENT.match(lines[k + 3]):
                break
            label, votes = " ".join(name), names.to_int(lines[k + 2])
            if not label.lower().startswith("write-in"):
                choices.append(Choice(label, votes, choice_id=label))
            name, k = [], k + 4
        is_measure = bool(re.match(r"(?i)(measure|proposition)\s+\w+", title))
        ident = None
        if is_measure:
            for c in choices:
                c.name = names.yes_no(c.name)
            ident = re.match(r"(?i)(?:measure|proposition)\s+([A-Z]{1,2}|\d+)", title).group(1).lower()
        kind = "measure" if is_measure else names.office_type(title)
        share = kind in HART_SHARE_KINDS or bool(re.match(r"(?i)proposition \d", title)) \
            or bool(re.search(r"(?i)supreme court|court of appeal|\bapp dist\b", title))
        contest = Contest(
            source="ca.santa_barbara", contest_id=heading, state="CA", title=title, office_type=kind,
            district=ident if is_measure else names.district(title), jurisdiction="Santa Barbara County",
            scope="partial" if share else "complete", vote_for=vote_for,
            reporting=Reporting(names.to_int(done.group(1)), names.to_int(done.group(2))) if done else Reporting(),
            url=url, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
        # Without a write-in table the next contest's title follows the last choice directly.
        pending, i = (name if k < len(lines) and lines[k] == "Precincts" else []), k
    return contests


class SantaBarbara(Source):
    id = "ca.santa_barbara"
    state = "CA"
    level = "county"
    county = "Santa Barbara"
    title = "Santa Barbara County Elections results"
    site_name = "Santa Barbara County Elections"
    url = "https://www.countyofsb.org/acr-elections-election-results"
    platform = "Election Summary Report (HTML)"
    tiers = frozenset({4})

    @property
    def report_url(self) -> str:
        day = config.ELECTION_DATE
        return f"https://www.sbcvote.com/Elections/results/{day.year}{day:%b}{day:%d}/results-1.htm".replace(
            f"{day:%b}", f"{day:%b}".lower())

    def pull(self, fetch):
        try:
            page = fetch.get(self.report_url, expect="text")
        except Exception as exc:
            if "404" in str(exc):
                raise NotPublished(f"{self.report_url} isn't posted") from exc
            raise
        when = f"{config.ELECTION_DATE:%B} {config.ELECTION_DATE.day}, {config.ELECTION_DATE.year}"
        if f"{when} General Election" not in word_lines(page)[:10]:
            raise NotPublished(f"{self.report_url} isn't the {when} election")
        return parse_santa_barbara(page, url=self.report_url)


def clarity_county(name: str, eid: str | None = None) -> ClaritySource:
    return ClaritySource(f"ca.{name.lower().replace(' ', '_')}", "CA", f"{name} County (Clarity)",
                         f"{name} County", f"CA/{name.replace(' ', '_')}", tiers=(4,), level="county", county=name,
                         eid=eid)


# Nov 3 election ids linked from each county's site; Clarity's elections.json lists nothing for these counties.
_CLARITY_EIDS = {"Sonoma": "127275", "Contra Costa": "127405", "Santa Clara": "127570", "Ventura": "127362"}


SOURCES = [
    LosAngeles(),
    LiveVoterTurnoutSource("ca.orange", "CA", "Orange", "https://ocvote.gov/results/current-election-results",
                           f"{config.ELECTION_DATE.year} General Election"),
    LiveVoterTurnoutSource("ca.san_diego", "CA", "San Diego", "https://sdvote.com/results",
                           "Gubernatorial General Election"),
    LiveVoterTurnoutSource("ca.san_mateo", "CA", "San Mateo",
                           "https://www.smcacre.gov/elections/november-3-2026-election-results",
                           "Statewide General Election"),
    # San Bernardino's results page (elections.sbcounty.gov/elections/2026/1103/results/) forwards browsers here.
    LiveVoterTurnoutSource("ca.san_bernardino", "CA", "San Bernardino",
                           "https://www.livevoterturnout.com/ENR/sanbernardinocaenr/3/en/Index_3.html",
                           "November 3, 2026, General Election"),
    *[clarity_county(n, _CLARITY_EIDS.get(n)) for n in ("Santa Clara", "Contra Costa", "Sonoma", "Ventura", "Marin")],
    Alameda(),
    SantaCruz(),
    SantaBarbara(),
    HartVeritySource("ca.stanislaus", "CA", "Stanislaus", "https://www.stanvote.gov/past-results/results.htm",
                     "Stanislaus County Registrar of Voters"),
    # Solano's registrar page still links its 2024 results (18); the Nov 3, 2026 general is 21.
    LiveVoterTurnoutSource("ca.solano", "CA", "Solano",
                           "https://www.livevoterturnout.com/ENR/solanocaenr/21/en/Index_21.html",
                           f"{config.ELECTION_DATE.year} November General"),
    EnhancedVotingSource("ca.sacramento", "CA", "Sacramento County (Enhanced Voting)",
                         "Sacramento County Voter Registration & Elections", "https://results.saccounty.gov",
                         "sacramento-county-ca", tiers=(4,), level="county", county="Sacramento"),
]
