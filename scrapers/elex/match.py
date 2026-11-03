"""Ties each WFP endorsement to one contest and one choice, and keeps the review file data/results/matches.csv.

Matching, in order (details in docs/election-results-scraper-plan.md, "Matching results to endorsements"):

1. Measures: the measure number/letter within the state; the choice is WFP's position (Yes/No).
2. Candidates: same office type and district, then surname.             -> auto
3. Same office type in any district (WFP listed the wrong district).     -> needs_review
4. Local and judicial races: any contest in the state with the surname
   and first name; auto when the contest title shares a word with the
   WFP office, otherwise needs_review.
5. Several equally good candidates are never guessed                    -> needs_review

Scraped sources are tried first; manual entries only for rows no scraped source matched.

Review: set `status` to `confirmed`, or fix source/contest_id/choice_id and set `method` to `manual`. Rows that are
confirmed or manual are never changed by the matcher; everything else is re-evaluated on every run.
"""
import csv
from collections import defaultdict
from dataclasses import dataclass

from . import config, names
from .model import Choice, Contest

COLUMNS = ["wfp_id", "state", "name", "office", "status", "method", "source", "contest_id", "contest_title",
           "choice_id", "choice", "note"]

AUTO, NEEDS_REVIEW, CONFIRMED, UNMATCHED, NOT_ON_BALLOT, NO_SOURCE = (
    "auto", "needs_review", "confirmed", "unmatched", "not_on_ballot", "no_source")

# A WFP office type can also be found in these contest types (NM elects governor and lieutenant governor jointly).
ALSO_IN = {"lt_governor": ("governor",)}

# Words too common in office names to show two offices are the same.
_STOP = {"of", "the", "and", "for", "county", "state", "district", "city", "member", "seat", "office", "position",
         "pos", "at", "large", "no", "vote", "1", "2", "3", "4", "5", "6", "7", "8", "9"}


@dataclass
class Match:
    status: str
    method: str = ""
    contest: Contest | None = None
    choice: Choice | None = None
    note: str = ""


def _has_surname(choice: Choice, surname: str) -> bool:
    return surname in names.tokens(choice.name)


def _has_first_name(choice: Choice, first: str) -> bool:
    toks = names.tokens(choice.name)
    return first in toks or (len(first) == 1 and any(t.startswith(first) for t in toks))


# Office nouns, so the near-name fallback only trusts a shared place name ("Socorro", "East Providence").
_OFFICE_WORDS = {"council", "board", "school", "committee", "commission", "commissioner", "mayor", "trustee",
                 "trustees", "education", "town", "ward", "area", "supervisors", "non", "partisan", "court",
                 "judge", "sheriff", "attorney", "unified", "union", "high", "elementary", "director", "directors"}


def _overlap(office: str, title: str, ignore=frozenset()) -> int:
    skip = _STOP | ignore
    return len((set(names.tokens(office)) - skip) & (set(names.tokens(title)) - skip))


def _pick(hits: list[tuple[Contest, Choice]], row: dict) -> tuple[tuple[Contest, Choice] | None, str]:
    """One (contest, choice) from several surname hits: first name, then office-title overlap. None if tied."""
    if len(hits) > 1:
        first = names.first_name(row["name"])
        narrowed = [h for h in hits if _has_first_name(h[1], first)]
        hits = narrowed or hits
    if len(hits) > 1:
        scores = [_overlap(row["office"], c.title) for c, _ in hits]
        best = max(scores)
        hits = [h for h, s in zip(hits, scores) if s == best]
    if len(hits) == 1:
        return hits[0], ""
    return None, "ambiguous: " + "; ".join(f"{c.title} / {ch.name}" for c, ch in hits[:4])


def _surname_hits(contests, surname):
    return [(c, ch) for c in contests for ch in c.choices if _has_surname(ch, surname)]


def match_one(row: dict, contests: list[Contest]) -> Match:
    """Match one endorsement against one state's contests (from one tier of sources)."""
    kind = names.wfp_office_type(row)
    if kind == "measure":
        ident = names.measure_id(row["name"])
        hits = [c for c in contests if c.office_type == "measure" and ident and c.district == ident]
        if len(hits) != 1:
            return Match(UNMATCHED if not hits else NEEDS_REVIEW,
                         note=f"measure {ident!r}: " + ("not found" if not hits else f"{len(hits)} contests"))
        position = names.yes_no(row.get("position") or "Yes")
        position = position if position in ("Yes", "No") else "Yes"
        choice = next((ch for ch in hits[0].choices if ch.name == position), None)
        if choice is None:
            return Match(NEEDS_REVIEW, "measure_number", hits[0], note=f"no {position!r} choice in contest")
        return Match(AUTO, "measure_number", hits[0], choice)

    surname = names.surname(row["name"])
    if not surname:
        return Match(UNMATCHED, note="no surname in WFP name")
    types = (kind, *ALSO_IN.get(kind, ()))
    same_type = [c for c in contests if c.office_type in types]
    wanted_district = names.district(row["office"]) if kind not in ("local", "judicial") else None
    if wanted_district and kind not in ("governor", "lt_governor", "attorney_general", "secretary_of_state",
                                        "insurance_commissioner", "federal_senate"):
        in_district = [c for c in same_type if c.district == wanted_district]
    else:
        in_district = same_type
    if kind not in ("local", "judicial"):
        hits = _surname_hits(in_district, surname)
        if hits:
            picked, note = _pick(hits, row)
            if picked:
                return Match(AUTO, "district_surname", *picked)
            return Match(NEEDS_REVIEW, "district_surname", note=note)
        hits = _surname_hits(same_type, surname)
        if hits:
            picked, note = _pick(hits, row)
            if picked:
                return Match(NEEDS_REVIEW, "surname_any_district", *picked,
                             note=f"district differs from WFP listing ({wanted_district} -> {picked[0].district})")
            return Match(NEEDS_REVIEW, "surname_any_district", note=note)

    # Local, judicial, or a state office filed under an unexpected type: search the whole state, but require the
    # first name too, since common surnames turn up across hundreds of local contests.
    first = names.first_name(row["name"])
    by_surname = _surname_hits(contests, surname)
    hits = [(c, ch) for c, ch in by_surname if _has_first_name(ch, first)]
    if hits:
        picked, note = _pick(hits, row)
        if not picked:
            return Match(NEEDS_REVIEW, "name_in_state", note=note)
        contest, choice = picked
        if _overlap(row["office"], contest.title) and kind in ("local", "judicial"):
            return Match(AUTO, "name_in_state", contest, choice)
        return Match(NEEDS_REVIEW, "name_in_state", contest, choice,
                     note=f"found by name only; check the office ({contest.title})")
    # Near misses, for review: a nickname ("Jackie" for Jacqueline) or a misspelled surname ("Power" for Powell),
    # but only in a contest whose title shares a place name with the WFP office.
    office_district = names.district(row["office"])
    near = [(c, ch, "first name differs") for c, ch in by_surname if _overlap(row["office"], c.title, _OFFICE_WORDS)]
    if not near:
        near = [(c, ch, "surname differs") for c in contests for ch in c.choices
                if _has_first_name(ch, first) and _overlap(row["office"], c.title, _OFFICE_WORDS)
                and (office_district is None or c.district == office_district)]
    if len(near) == 1:
        contest, choice, why = near[0]
        return Match(NEEDS_REVIEW, "near_name", contest, choice, note=f"{why}: WFP {row['name']!r}, "
                                                                      f"feed {choice.name!r}")
    if near:
        return Match(NEEDS_REVIEW, "near_name", note="ambiguous: " + "; ".join(
            f"{c.title} / {ch.name}" for c, ch, _ in near[:4]))
    return Match(UNMATCHED, note=f"no {surname!r} in any {row['state_code']} contest loaded")


def read_review_file() -> dict[str, dict]:
    if not config.MATCHES_FILE.exists():
        return {}
    with config.MATCHES_FILE.open(encoding="utf-8", newline="") as f:
        return {f"{r['state']}|{r['name']}|{r['office']}": r for r in csv.DictReader(f)}


def _row_for(e: dict, m: Match) -> dict:
    return {"wfp_id": e["id"], "state": e["state_code"], "name": e["name"], "office": e["office"],
            "status": m.status, "method": m.method, "source": m.contest.source if m.contest else "",
            "contest_id": m.contest.contest_id if m.contest else "", "contest_title": m.contest.title if m.contest
            else "", "choice_id": m.choice.choice_id if m.choice else "", "choice": m.choice.name if m.choice else "",
            "note": m.note}


def match_all(endorsements: list[dict], contests: list[Contest], previous: dict[str, dict],
              local_states: set[str] = frozenset()) -> list[dict]:
    """The full review table: kept rows for confirmed/manual entries, fresh matches for everything else.
    `local_states` are states with a source that carries local races; elsewhere an unmatched local or judicial
    race is `no_source`, not `unmatched`."""
    scraped, manual = defaultdict(list), defaultdict(list)
    for c in contests:
        (manual if c.source == "manual" else scraped)[c.state].append(c)
    out = []
    for e in endorsements:
        kept = previous.get(e["key"])
        if kept and (kept.get("status") == CONFIRMED or kept.get("method") == "manual"):
            out.append({**{k: kept.get(k, "") for k in COLUMNS}, "wfp_id": e["id"]})
            continue
        if e["nov3_ballot"] == "no":
            out.append(_row_for(e, Match(NOT_ON_BALLOT, note=e.get("nov3_note", "")[:200])))
            continue
        state = e["state_code"]
        if not scraped[state] and not manual[state]:
            out.append(_row_for(e, Match(NO_SOURCE, note=f"no source covers {state} yet")))
            continue
        m = match_one(e, scraped[state]) if scraped[state] else Match(UNMATCHED)
        if m.status == UNMATCHED and manual[state]:
            manual_match = match_one(e, manual[state])
            if manual_match.status != UNMATCHED:
                m = manual_match
        if m.status == UNMATCHED and not scraped[state]:
            m = Match(NO_SOURCE, note=f"no scraper for {state}; not in manual entries")
        elif m.status == UNMATCHED and state not in local_states and names.wfp_office_type(e) in ("local",
                                                                                                   "judicial"):
            m = Match(NO_SOURCE, note=f"{state}'s scraped sources don't carry local races yet")
        out.append(_row_for(e, m))
    return out


def write_review_file(rows: list[dict]) -> None:
    config.MATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    order = {NEEDS_REVIEW: 0, UNMATCHED: 1, AUTO: 2, CONFIRMED: 3, NO_SOURCE: 4, NOT_ON_BALLOT: 5}
    rows = sorted(rows, key=lambda r: (order.get(r["status"], 9), r["state"], int(r["wfp_id"] or 0)))
    tmp = config.MATCHES_FILE.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(config.MATCHES_FILE)


def counts(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for r in rows:
        out[r["status"]] += 1
    return dict(sorted(out.items()))


def changes(old: dict[str, dict], new: list[dict]) -> list[str]:
    """Readable lines for rows whose status or matched choice changed, for the run log."""
    lines = []
    for r in new:
        before = old.get(f"{r['state']}|{r['name']}|{r['office']}")
        if before and (before["status"], before["contest_id"], before["choice_id"]) == (
                r["status"], r["contest_id"], r["choice_id"]):
            continue
        was = before["status"] if before else "new"
        lines.append(f"match {r['state']} {r['name']} ({r['office']}): {was} -> {r['status']}"
                     + (f" [{r['contest_title']} / {r['choice']}]" if r["contest_id"] else "")
                     + (f" {r['note']}" if r["note"] else ""))
    return lines

