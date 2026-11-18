"""How competitive were WFP's endorsed races, and how did WFP do in the competitive ones?

  .venv/bin/python analysis/competitiveness.py        # writes docs/competitive-races.md

Competitiveness is measured after the fact, from the vote: each endorsement's head-to-head margin against the rival
across the winning line (the first loser if WFP's pick is winning, the last winner if not), as a share of the two's
combined votes. For a two-way race that's the usual margin in points. Bands:

  tossup < 5 points, lean 5-10, likely 10-20, safe 20+, uncontested (no rival on the ballot)

"Competitive" means tossup or lean (under 10 points). Race kinds:
  partisan                 WFP's pick and the rival are from different parties (almost always D/WFP vs R)
  nonpartisan/intra-party  nonpartisan offices, and same-party races (California top-two, NY primaries carried over)
  measure                  ballot measures; WFP's side is its Yes/No position
"""
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data" / "results"
OUT = REPO / "docs" / "competitive-races.md"
COUNTED = ("counting", "final")
BANDS = ["tossup", "lean", "likely", "safe", "uncontested"]
BAND_LABEL = {"tossup": "Tossup (<5 pts)", "lean": "Lean (5–10)", "likely": "Likely (10–20)", "safe": "Safe (20+)",
              "uncontested": "Uncontested"}


def load(path):
    return json.loads(Path(path).read_text())


def seats_by_contest():
    out = {}
    for f in (RESULTS / "latest").glob("*.json"):
        for c in load(f).get("contests") or []:
            out[(f.stem, c.get("title"))] = c.get("vote_for") or 1
    return out


def band(margin):
    a = abs(margin)
    return "tossup" if a < 5 else "lean" if a < 10 else "likely" if a < 20 else "safe"


def rows():
    published = load(RESULTS / "wfp_results.json")
    candidates = {str(c["id"]): c for c in load(REPO / "data" / "candidates.json")["candidates"]}
    seats = seats_by_contest()
    out = []
    for cid, r in published["results"].items():
        c = candidates[cid]
        row = {"id": cid, "name": c["name"], "state": c["state"], "category": c["office_category"],
               "office": c["office"], "status": r["status"], "contest": r.get("contest") or ""}
        out.append(row)
        if r["status"] not in COUNTED:
            row["band"] = None
            continue
        row["won"] = bool(r.get("wfp_leading"))
        choices = r.get("choices") or []
        wfp = next((x for x in choices if x.get("is_wfp")), None)
        n = seats.get((r.get("source"), r.get("contest")), 1)
        others = sorted((x for x in choices if not x.get("is_wfp") and not x["name"].lower().startswith("write")),
                        key=lambda x: -x["votes"])
        row["seats"] = n
        if r.get("uncontested") or not wfp or len(others) < n:
            row.update(band="uncontested", margin=None, kind="uncontested")
            continue
        rival = others[n - 1]
        margin = (wfp["votes"] - rival["votes"]) / max(1, wfp["votes"] + rival["votes"]) * 100
        if c["office_category"] == "Ballot Measure":
            kind = "measure"
        elif wfp.get("party") and rival.get("party") and names_party(wfp) != names_party(rival):
            kind = "partisan"
        else:
            kind = "nonpartisan/intra-party"
        row.update(margin=margin, band=band(margin), kind=kind, rival=rival["name"], rival_party=rival.get("party"),
                   rcv="first-choice" in row["contest"], wfp_party=names_party(wfp))
    return published, out


RATINGS = REPO / "data" / "ratings"
FORECASTERS = ("cook", "inside_elections", "sabato")
_STRENGTH = {"solid": 3, "safe": 3, "likely": 2, "lean": 1, "tilt": 0.5, "tossup": 0}
RATING_ORDER = ["Safe WFP", "Likely WFP", "Lean WFP", "Tossup", "Lean opponent", "Likely opponent", "Safe opponent"]


def rating_score(text):
    """'Lean D (flip)' -> +1, 'Likely R' -> -2, 'Tossup' -> 0 (positive favors Democrats)."""
    words = text.lower().split()
    strength = _STRENGTH[words[0]]
    return 0 if strength == 0 else strength if words[1] == "d" else -strength


def rating_label(score):
    """Average forecaster score from WFP's side (WFP's picks in these races are all Democrats)."""
    a = abs(score)
    if a < 0.5:
        return "Tossup"
    level = "Safe" if a >= 2.5 else "Likely" if a >= 1.5 else "Lean"
    return f"{level} {'WFP' if score > 0 else 'opponent'}"


def load_ratings():
    """{(kind, key): (avg score, 'Cook / IE / Sabato' text)} from data/ratings/*.csv (final pre-election ratings,
    copied from Wikipedia's ratings tables, which cite each forecaster)."""
    import csv
    out = {}
    for kind, key in (("house", "district"), ("senate", "state"), ("governor", "state")):
        with open(RATINGS / f"{kind}_2026.csv", newline="") as f:
            for row in csv.DictReader(f):
                scores = [rating_score(row[k]) for k in FORECASTERS]
                out[(kind, row[key])] = (sum(scores) / len(scores), " / ".join(row[k] for k in FORECASTERS))
    return out


def rate(row, ratings):
    """Attach the pre-election rating for House, Senate and governor (and lieutenant governor) races."""
    import re
    office = row["office"].lower()
    if row["category"] == "Federal House":
        n = re.search(r"district (\d+)", office)
        if not n:
            return
        kind, key = "house", f"{row['state']} {n.group(1)}"
    elif row["category"] == "Federal Senate":
        kind, key = "senate", row["state"]
    elif row["category"] == "State Executive" and re.match(r"(lt\.? |lieutenant )?governor$", office):
        kind, key = "governor", row["state"]
    else:
        return
    if row.get("kind") != "partisan":
        row["rating"] = "Not rated (same-party race)"
        return
    found = ratings.get((kind, key))
    if found:
        row["rating"], row["rating_text"] = rating_label(found[0]), found[1]
    else:
        # Every forecaster rates unlisted districts safe for the party that holds them; nearly always the winner.
        row["rating"] = "Safe WFP" if row["won"] else "Safe opponent"
        row["rating_text"] = "not on forecasters' competitive lists"


PRIOR_STATES = {"New York": "NY", "Connecticut": "CT", "Pennsylvania": "PA", "Colorado": "CO", "California": "CA",
                "Oregon": "OR", "Georgia": "GA", "New Mexico": "NM", "Wisconsin": "WI", "Arizona": "AZ", "Ohio": "OH",
                "Massachusetts": "MA"}
SKIP_LABEL = {"uncontested": "uncontested this year", "nonpartisan/intra-party": "same-party races this year",
              "partisan": "contested races with no comparable last result (Ohio Senate, Massachusetts Senate)"}
PRIOR_ORDER = RATING_ORDER + ["No Republican last time", "No Democrat last time"]


def load_prior():
    """{(state, chamber, district): (year, D strength, R strength)} from data/ratings/state_leg_prior.csv.

    A party's strength is its top candidate's votes; in a district that elects two (Arizona's House) it's the average
    of the party's top two (or its one candidate, if it ran one)."""
    import csv
    found = collections.defaultdict(lambda: {"D": [], "R": []})
    meta = {}
    with open(RATINGS / "state_leg_prior.csv", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["state"], r["chamber"], r["district"])
            meta[key] = (int(r["year"]), int(r["seats"]))
            if r["party"] in ("D", "R"):
                found[key][r["party"]].append(int(r["votes"]))
    out = {}
    for key, (year, n) in meta.items():
        top = {p: sorted(found[key][p], reverse=True)[:n] for p in ("D", "R")}
        out[key] = (year, *(sum(v) / len(v) if v else 0 for v in (top["D"], top["R"])))
    return out


def prior_label(margin):
    """The seat's last result, D minus R as a share of the two, labeled from WFP's side with the same bands."""
    a = abs(margin)
    if a < 5:
        return "Tossup"
    level = "Lean" if a < 10 else "Likely" if a < 20 else "Safe"
    return f"{level} {'WFP' if margin > 0 else 'opponent'}"


def rate_prior(row, seats):
    """Attach the seat's previous result to a partisan legislative race in one of PRIOR_STATES."""
    import re
    st = PRIOR_STATES.get(row["state"])
    chamber = {"State House": "state_house", "State Senate": "state_senate"}.get(row["category"])
    # The matched contest's district first: the endorsement text has typos ("Distrcit 6"; Damon Connolly is listed
    # for Senate District 12 but ran in District 2).
    n = re.search(r"distr\w* (\d+)", row["contest"].lower()) or re.search(r"distr\w* (\d+)", row["office"].lower())
    if n:
        district = str(int(n.group(1)))
    else:  # named districts (Massachusetts): "Massachusetts State House, 16th Middlesex District"
        sys.path.insert(0, str(REPO / "analysis"))
        from prior_results import district_key
        district = district_key(row["office"].split(",", 1)[-1])
    if not (st and chamber and row.get("kind") == "partisan"):
        return
    found = seats.get((st, chamber, district))
    if not found:
        return
    year, d, rep = found
    # WFP's picks are Democrats or independents against a Republican: read the seat from the Democratic side, and
    # flip it only for a Republican pick.
    sign = -1 if row.get("wfp_party") == "REP" else 1
    row["prior_year"] = year
    if d and rep:
        row["prior_margin"] = sign * (d - rep) / (d + rep) * 100
        row["prior"] = prior_label(row["prior_margin"])
    else:
        row["prior_margin"] = None
        row["prior"] = "No Republican last time" if (d and sign > 0) or (rep and sign < 0) else "No Democrat last time"


def prior_section(counted):
    """How each legislative seat voted last time, against how WFP's pick did this time."""
    seats = load_prior()
    for r in counted:
        rate_prior(r, seats)
    rated = [r for r in counted if r.get("prior")]
    leg = [r for r in counted if r["state"] in PRIOR_STATES and r["category"] in ("State House", "State Senate")]
    skipped = collections.Counter(r["kind"] for r in leg if not r.get("prior"))
    md = ["## Before the election: last result in the seat (state legislatures in twelve states)",
          "",
          "Forecasters don't rate state legislative seats, so these use each seat's previous general election "
          "on the same district lines, for the twelve states with the most WFP legislative races: New York, Connecticut, "
          "Pennsylvania, Oregon, New Mexico, Colorado, Georgia, Wisconsin, California, Ohio, Arizona and "
          "Massachusetts. Lower chambers use 2024. Senate seats use the last "
          "time they were on the ballot, 2024 or 2022, since most state senators serve four-year terms. The margin "
          "is the top Democrat's votes (all party lines) against the top Republican's, from WFP's side, in the same "
          "bands as above. Only races with a Democrat and a Republican on the 2026 ballot are rated. California's "
          "top-two system means some seats had no Republican (or no Democrat) in the last general. Sources: the "
          "states' official results for NY, CT, PA, CO and GA, Wikipedia's district tables for CA, OR, NM, WI, AZ, OH and MA. "
          "Wisconsin's and Ohio's Senates are left out: their 2026 seats were last elected in 2022, on maps "
          "replaced since. Arizona elects two House members per district; there each party's strength is the "
          "average of its top two candidates. "
          "Most Wisconsin endorsements have no 2026 results source yet, so few are rated. Built by "
          "`analysis/prior_results.py` into `data/ratings/state_leg_prior.csv`.",
          "",
          f"{len(rated)} of the {len(leg)} legislative endorsements with results in these states are rated; the rest "
          "are " + ", ".join(f"{n} {SKIP_LABEL.get(k, k)}" for k, n in skipped.most_common()) + ".",
          "",
          "Last time's result says nothing about who was running: an open seat, a new challenger, a seat no "
          "one contested last time, or an incumbent who changed parties (Cyrus Javadi, OR-32) can all play "
          "differently.",
          "",
          "| Last result | Races | Won | Ended under 10 pts | Moved toward WFP |",
          "|---|---:|---:|---:|---:|"]
    for label in PRIOR_ORDER:
        g = [r for r in rated if r["prior"] == label]
        if not g:
            continue
        moved = [r for r in g if r["prior_margin"] is not None]
        toward = f"{sum(1 for r in moved if r['margin'] > r['prior_margin'])} of {len(moved)}" if moved else "–"
        md.append(f"| {label} | {len(g)} | {sum(r['won'] for r in g)} "
                  f"| {sum(1 for r in g if r['band'] in ('tossup', 'lean'))} | {toward} |")
    md += ["", "By state:", "",
           "| State | Rated | Won | Was close last time (<10) | Won | Was safe opponent | Won |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for state in PRIOR_STATES:
        g = [r for r in rated if r["state"] == state]
        close = [r for r in g if r["prior"] in ("Tossup", "Lean WFP", "Lean opponent")]
        long = [r for r in g if r["prior"] in ("Safe opponent", "No Democrat last time")]
        md.append(f"| {state} | {len(g)} | {sum(r['won'] for r in g)} | {len(close)} | "
                  f"{sum(r['won'] for r in close)} | {len(long)} | {sum(r['won'] for r in long)} |")
    notable = [r for r in rated if r["prior"] not in ("Safe WFP", "Likely WFP", "No Republican last time",
                                                      "Safe opponent", "No Democrat last time")
               or r["band"] in ("tossup", "lean") or (r["won"] != (r["prior"].endswith("WFP")
                                                                 or r["prior"] == "No Republican last time"))]
    md += ["",
           "Seats that were within 10 points or leaned to the opponent last time, plus any seat that ended under "
           "10 points or changed party this time:",
           "",
           "| Last result | Last margin | Final margin | | Candidate | State | Office |",
           "|---|---:|---:|---|---|---|---|"]
    for r in sorted(notable, key=lambda r: (PRIOR_ORDER.index(r["prior"]), -(r["prior_margin"] or 0))):
        last = f"{r['prior_margin']:+.1f} ({r['prior_year']})" if r["prior_margin"] is not None else f"– ({r['prior_year']})"
        md.append(f"| {r['prior']} | {last} | {r['margin']:+.1f} | {'Won' if r['won'] else 'Lost'} "
                  f"| {r['name']} | {r['state']} | {r['office']} |")
    return md + [""]


def names_party(choice):
    # Sources write Republicans as REP or R, Democrats as DEM or D; WFP lines count as Democratic here.
    p = (choice.get("party") or "").upper()
    return {"R": "REP", "D": "DEM", "WFP": "DEM", "WOR": "DEM"}.get(p, p)


def pct(won, n):
    return f"{won / n:.0%}" if n else "–"


def table(counted, key, order=None, min_competitive=0):
    groups = collections.defaultdict(list)
    for r in counted:
        groups[key(r)].append(r)
    keys = order or sorted(groups, key=lambda k: -sum(1 for r in groups[k] if r["band"] in ("tossup", "lean")))
    lines = ["| | Races | Won | Competitive (<10) | Won | Win rate | Tossups (<5) | Won |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k in keys:
        g = groups.get(k, [])
        comp = [r for r in g if r["band"] in ("tossup", "lean")]
        toss = [r for r in g if r["band"] == "tossup"]
        if not g or len(comp) < min_competitive:
            continue
        lines.append(f"| {k} | {len(g)} | {sum(r['won'] for r in g)} | {len(comp)} | {sum(r['won'] for r in comp)} "
                     f"| {pct(sum(r['won'] for r in comp), len(comp))} | {len(toss)} | {sum(r['won'] for r in toss)} |")
    return "\n".join(lines)


def race_list(items):
    lines = ["| Margin | | Candidate | State | Office | Rival |", "|---:|---|---|---|---|---|"]
    for r in sorted(items, key=lambda r: r["margin"]):
        rival = f"{r['rival']} ({r['rival_party']})" if r.get("rival_party") else r["rival"]
        note = " (RCV first choices)" if r.get("rcv") else ""
        lines.append(f"| {r['margin']:+.1f} | {'Won' if r['won'] else 'Lost'} | {r['name']} | {r['state']} "
                     f"| {r['office']}{note} | {rival} |")
    return "\n".join(lines)


def ratings_section(counted):
    """Pre-election ratings against outcomes, for the races forecasters rate (House, Senate, governor)."""
    ratings = load_ratings()
    for r in counted:
        rate(r, ratings)
    rated = [r for r in counted if r.get("rating") in RATING_ORDER]
    same_party = [r for r in counted if r.get("rating", "").startswith("Not rated")]
    md = ["## Before the election: forecaster ratings (House, Senate, governor)",
          "",
          "The final pre-election ratings from Cook Political Report, Inside Elections and Sabato's Crystal Ball "
          "(Oct 29 – Nov 2), averaged (Solid/Safe 3, Likely 2, Lean 1, Tilt ½, Tossup 0) and read from WFP's side. "
          "Copied from Wikipedia's ratings tables into `data/ratings/`. House districts missing from those tables "
          "were rated safe by all three. Same-party races (California's top-two) have no party rating and are left "
          f"out ({len(same_party)}: " + ", ".join(r["name"] for r in same_party) + ").",
          "",
          "| Rating | Races | Won | Ended under 10 pts |",
          "|---|---:|---:|---:|"]
    for label in RATING_ORDER:
        g = [r for r in rated if r["rating"] == label]
        if g:
            md.append(f"| {label} | {len(g)} | {sum(r['won'] for r in g)} "
                      f"| {sum(1 for r in g if r['band'] in ('tossup', 'lean'))} |")
    md += ["",
           "| Rating | Cook / IE / Sabato | Final margin | | Candidate | State | Office |",
           "|---|---|---:|---|---|---|---|"]
    for r in sorted(rated, key=lambda r: (RATING_ORDER.index(r["rating"]), -r["margin"])):
        md.append(f"| {r['rating']} | {r['rating_text']} | {r['margin']:+.1f} | {'Won' if r['won'] else 'Lost'} "
                  f"| {r['name']} | {r['state']} | {r['office']} |")
    return md + [""]


def main():
    published, all_rows = rows()
    counted = [r for r in all_rows if r["status"] in COUNTED]
    missing = collections.Counter(r["status"] for r in all_rows if r["status"] not in COUNTED)
    by_band = {b: [r for r in counted if r["band"] == b] for b in BANDS}
    comp = by_band["tossup"] + by_band["lean"]
    contested = [r for r in counted if r["band"] != "uncontested"]

    md = [f"# How competitive were WFP's races?",
          "",
          f"Generated by `analysis/competitiveness.py` from results run {published['run_id']} "
          f"({published['generated_at'][:16]}Z). Counts are still unofficial in many places; races under a point "
          "can still move.",
          "",
          "## Method",
          "",
          "- **Margin:** WFP's pick against the rival across the winning line (first loser if WFP's pick is winning, "
          "last winner if not), as a share of the two's combined votes. For a two-way race it's the usual margin.",
          "- **Bands:** tossup under 5 points, lean 5–10, likely 10–20, safe 20+. **Competitive** = under 10.",
          "- **Kinds:** *partisan* (different parties, almost always Democrat/WFP vs Republican); "
          "*nonpartisan/intra-party* (nonpartisan offices, and same-party races such as California's top-two); "
          "*measure* (WFP's Yes/No position).",
          "- This measures how close the race **ended up**, not how it looked beforehand. A seat rated safe that "
          "turned close counts as competitive here, and a targeted race that turned into a blowout doesn't.",
          "",
          f"**Coverage:** {len(counted):,} of {len(all_rows):,} endorsements have results. Not included: "
          + ", ".join(f"{n} {s.replace('_', ' ')}" for s, n in missing.most_common()) + ".",
          "",
          "## By competitiveness",
          "",
          "| Band | Races | Won | Win rate |",
          "|---|---:|---:|---:|"]
    for b in BANDS:
        g = by_band[b]
        md.append(f"| {BAND_LABEL[b]} | {len(g)} | {sum(r['won'] for r in g)} | {pct(sum(r['won'] for r in g), len(g))} |")
    md.append(f"| **All with results** | **{len(counted)}** | **{sum(r['won'] for r in counted)}** "
              f"| **{pct(sum(r['won'] for r in counted), len(counted))}** |")
    md += ["",
           f"{len(comp)} of {len(contested)} contested races ({len(comp) / len(contested):.0%}) were decided by under "
           f"10 points; WFP won {sum(r['won'] for r in comp)} of them ({pct(sum(r['won'] for r in comp), len(comp))}).",
           "",
           "## By kind of race",
           "",
           table(counted, lambda r: r["kind"], order=["partisan", "nonpartisan/intra-party", "measure", "uncontested"]),
           "",
           "## By office",
           "",
           table(counted, lambda r: r["category"]),
           "",
           "## By state (states with competitive races)",
           "",
           table(counted, lambda r: r["state"], min_competitive=1),
           "",
           "## Safe-seat losses",
           "",
           "Endorsements that lost by 20 points or more: mostly long shots in safe Republican seats, plus local and "
           "same-party races.",
           "",
           "| Kind | Office | Losses |", "|---|---|---:|",
           *(f"| {kind} | {cat} | {n} |" for (kind, cat), n in collections.Counter(
               (r["kind"], r["category"]) for r in by_band["safe"] if not r["won"]).most_common()),
           "",
           *ratings_section(counted),
           *prior_section(counted),
           "## Every competitive race (under 10 points)",
           "",
           race_list(comp),
           ""]
    OUT.write_text("\n".join(md))
    print(f"wrote {OUT.relative_to(REPO)}: {len(comp)} competitive races, {sum(r['won'] for r in comp)} won")


if __name__ == "__main__":
    main()
