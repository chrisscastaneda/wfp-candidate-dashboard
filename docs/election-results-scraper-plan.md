# Election results scrapers: implementation plan

How we'll collect Nov 3, 2026 results for WFP's endorsements without an AP or DDHQ license. This covers every
scraper module, the driver script that runs them, the files they write, and the order we'll build them in.
Requirements are in [prompts/election-results-scraper-planning.md](../prompts/election-results-scraper-planning.md);
the source research is in [election-results-sources.md](election-results-sources.md) and
[results_sources.csv](results_sources.csv).

Written Nov 2, 2026, the night before the election. No production code yet; two exploratory scripts are in
`scrapers/explore/` (see [What the probes found](#what-the-probes-found)).

## Contents

1. [Decisions so far](#decisions-so-far)
2. [Phase 1 status](#phase-1-status), [Phase 2 status](#phase-2-status) and [Phase 3 status](#phase-3-status)
3. [What the probes found](#what-the-probes-found)
4. [Design principles](#design-principles)
5. [Architecture](#architecture)
6. [Core modules](#core-modules)
7. [The normalized result model](#the-normalized-result-model)
8. [Matching results to endorsements](#matching-results-to-endorsements)
9. [Data contract for the dashboard](#data-contract-for-the-dashboard)
10. [Command-line interface](#command-line-interface)
11. [Files, history and logs](#files-history-and-logs)
12. [Scraper catalog](#scraper-catalog)
13. [Phases and coverage](#phases-and-coverage)
14. [Blocked and feed-less states](#blocked-and-feed-less-states)
15. [Testing](#testing)
16. [Election-night runbook](#election-night-runbook)
17. [Resolved and open questions](#resolved-and-open-questions)

## Decisions so far

| Topic | Decision |
|---|---|
| Data sources | Official and other free sources only; no AP/DDHQ |
| Priority | 1. U.S. House/Senate, 2. state legislative + statewide offices, 3. statewide ballot measures, 4. local (NY and CA first). Local races that come free with a higher-tier feed are collected with it |
| Build order | State-level scrapers first, then county scrapers |
| Hard sources | Deprioritized. We don't work around bot protection (Cloudflare challenges, 403s); those sources get a fallback instead |
| Timeline | Phased: a small set of state scrapers for Nov 3 night, then more states, counties, and updates through certification |
| Matching | Automatic, written to a review file you can correct; anything uncertain or unmatched is flagged |
| Dependencies | A few packages (`requests`, later `pdfplumber`, `pytest` for tests) in a virtualenv with `requirements.txt` |
| Run mode | Each run does one pull and exits; `--watch N` repeats every N minutes |
| Storage | Latest results plus timestamped history snapshots, in `data/results/` |
| Logs | A readable `.log` and a JSON summary for every run, in `logs/` |
| Dashboard | This plan defines the results file the dashboard will read; the UI work gets its own plan |
| Dashboard updates | You rebuild the dashboard and push a commit for each update. No runtime fetching |
| Where it runs | On your machine on election night. A scheduled GitHub Action can come later |
| Manual entries | Every federal race without a working scraper on Nov 3 night, including MI and FL (see [Manual federal races](#manual-federal-races)) |
| Feed requests | Not asking NY BOE or AZ SoS for media feeds for now |

## Phase 1 status

Built Nov 2–3 overnight. Ten sources are registered: `ca`, `pa`, `nc`, `ga`, `ut`, `wa`, `ri`, `nm`, `ne` and
`manual`. A live run takes about 18 seconds. The 23 tests run offline against the saved Nov 3 contest lists in
`tests/fixtures/`.

**Live check, 1am ET Nov 3:** 8 of 9 state sources returned their Nov 3 contests. Washington's site has opened
since the Nov 2 probe. Georgia's responds but doesn't list Nov 3 yet, so it reports `not_published` and needs no
change when it appears. Pennsylvania's per-office method turned out to be `GetOfficeData` with
`methodName=GetOfficeDetails`; the site's pages sit behind a bot check, but its JSON API answers scripts.

**Matching, before any votes:**

| Status | Rows | What it means |
|---|---:|---|
| `auto` | 164 | Every scraped state's federal, state and statewide-measure endorsements, plus local races the state feeds carry (NC sheriffs and DA, NM county commissions, Providence, Salt Lake County, King County, Seattle). Spot-checked: no false matches |
| `needs_review` | 5 | Connolly (WFP lists SD 12, he's on SD 2); "Cari Power" is Cari Leann **Powell** on the NM ballot; "Jackie" Goldman and "Libby" Merrill are Jacqueline and Elizabeth on the RI ballot; Tarkenton's office is "Prosecuting Attorney" in the feed |
| `unmatched` | 3 | **Not on Rhode Island's Nov 3 ballot:** Matt McCoy (HD 31, only James Sheehan is listed), Gena Felix (SD 8, only Lori Urso), Jonathan Jacobs (East Providence Ward 1). Probably primary losses; worth checking with WFP |
| `no_source` | 1,032 | States without a scraper yet, and local races in CA and NE, whose state feeds don't carry them |
| `not_on_ballot` | 12 | From `results_sources.csv` |

`manual-template` wrote 35 races to `manual_entries.csv`: the 34 in [Manual federal races](#manual-federal-races)
plus Georgia's House 1 while Georgia isn't publishing. Washington's House 7 is covered by its scraper now.

**Where the build differs from the layout above:**

- The Enhanced Voting and results-CSV states are configured in two modules, `states/enhanced_voting_states.py` and
  `states/results_csv_states.py`, instead of one file each. Each source is a few lines.
- `elex/endorsements.py` joins `candidates.json` with `results_sources.csv`. It keys rows by state + name + office,
  because candidate ids shift when WFP's list changes.
- Sources declare `local_races`. Where a state's feeds don't carry local races (CA, NE), unmatched local and judicial
  rows are `no_source` instead of `unmatched`, so `unmatched` stays a short list worth reading.
- `matches.csv` also uses `no_source`, plus a `near_name` method for nickname and misspelling matches. Those only
  count when the contest shares a place name with the WFP office, and they always go to review.
- In Utah, single-county legislative districts are only on county sub-sites, so `ut` also reads Salt Lake and Utah
  counties. North Carolina's county races come from its per-county files (Alamance, Durham, Mecklenburg).
- The candidate scraper logs each run to `logs/candidates/`, including rows added and removed since the last scrape.

## Phase 2 status

Built early Nov 3. Sixteen more sources, for 26 in all:

- **State sources:** `co`, `sc`, `fl` (Clarity), `ct`, `or`, `oh`, `de`, `md`.
- **County sources:** Clarity county sites `tx.bexar`, `tx.dallas`, `tx.denton`, `tx.tarrant`, `tx.travis`,
  `nj.hudson`, `nj.middlesex` and `oh.hamilton`.

A full live run takes about 70 seconds, mostly Ohio. The 30 offline tests pass.

**Live check, about 2am ET Nov 3:**

| Source | Status | Notes |
|---|---|---|
| Connecticut | ok, 82 of 82 matched | Static JSON under `ng-app/data/election/<id>/<version>/`. Fusion lines (DEM + WFP) are combined into one choice per candidate, with per-line votes in `party_lines` |
| Oregon | ok, 77 matched | CSV export is off, so this parses the results pages. House districts 31–60 need a form post-back (the "31 - 60" button), so the fetcher now supports POST |
| Ohio | ok, 25 matched | `getContestList` + `GetContestDetailsObject`, one request per contest (162), summed over counties. `HOST_GAPS` spaces those requests 0.25s apart |
| Delaware | ok, 13 of 13 | `Election_StatewideResults_ID_GE2026.json` has every contest, county races included |
| Maryland | ok, 9 of 9 | One page per House of Delegates district, plus county pages for county races |
| Denton County TX, Hamilton County OH | ok | Their Nov 3 elections are posted |
| Colorado, South Carolina, Florida, other TX and NJ counties | `not_published` | No Nov 3 election listed yet. They start working when it's posted. Colorado (85 rows) is the big one |

**Matching now:** 365 auto, 11 needs_review, 12 unmatched, 816 no_source, 12 not_on_ballot.

New review items and findings:

- **Oregon:**
  - "Angeline Nicole Basett" is Nicole **Bassett** on the SD 26 ballot.
  - Joe Hagedorn is Joseph on the ballot.
  - Three local measures (Astoria, Eugene, Hood River) were matched by title words, since WFP's names have no
    numbers.
  - **"Your 2 Cents" is measure 26-267** (Portland participatory budgeting). Its title shares no words with WFP's
    name, so set it by hand in `matches.csv`.
  - **Christina Stephenson** (Labor Commissioner) isn't on any Oregon results page. The office is nonpartisan, so
    she likely won outright in May.
- **Ohio:**
  - **"Senate Bill 396: Paid Family and Medical Leave"** isn't on the ballot; the only statewide issue is Issue 3.
  - **Columbus Issue 8** is in Franklin County, which has no source yet.
  - Cincinnati Issues 4 and 9 matched Hamilton County's numbered measures.
- **Texas:** the five county races (Bexar, Dallas, Tarrant, Travis) are unmatched until those counties post Nov 3.

**Blocked or deferred:**

- **Texas statewide** (`results.texas-election.com`) now serves a Cloudflare challenge. That's 1 row: Land
  Commissioner.
- **Minnesota** now redirects scripts to a Radware bot-manager check (2 rows).
- **DC** pushes results over SignalR behind a Cloudflare script (8 rows). Robert White is in the manual entries.
- **Louisiana** hasn't posted its Nov 3 files, and **Arkansas** has an open API but only 1 row. Both are left for
  later.

**Design changes in Phase 2:**

- County sources mark their share of state and federal contests `partial`, and the matcher ignores partial contests.
- Measures with the same number are told apart by place name: several Colorado counties have a "1A". A local measure
  also needs a shared place name, so "Columbus Issue 8" doesn't match Hamilton County's measure 8.
- A state with only county sources reports its statewide rows as `no_source`, not `unmatched`.
- A missing county or locality no longer fails the whole source. Its races just show as unmatched.
- The change hash ignores feed timestamps, so Nebraska's per-request timestamp doesn't write a history snapshot on
  every poll.

## Phase 3 status

Started early Nov 3. Phase 3 is **partly built**: most county sites, and NYC's ENR, don't show their Nov 3 results
format until results start tonight. Parsers written blind would be guesses, so those counties are listed below with
what to check when they go live.

**Built (7 county sources, 34 tests passing):**

| Source | Status | Notes |
|---|---|---|
| `ca.los_angeles` | ok, 24 of 29 matched | `results.lavote.gov/ElectionResults/GetElectionData`, JSON with the full Nov 3 ballot already loaded |
| `ca.orange` | ok, 20 of 21 matched | New platform module `platforms/livevoterturnout.py`. The results page link (with a random token) is read from ocvote.gov, newest election first |
| `ca.santa_clara`, `ca.contra_costa`, `ca.sonoma`, `ca.ventura`, `ca.marin` | `not_published` | Clarity configuration only (35 rows). Their `elections.json` lists are empty until they post |
| `ny.nyc` | ok, 55 matched | Built on election night (`counties/ny.py`). `enr.boenyc.gov` has an "Expand List" page per office with every district, each candidate's party lines, and "Percentage of Scanners Reported". A "*" after a title marks the city's share of a race that crosses the city line (statewide offices, NY-3, NY-16, SD-34, SD-36); those are partial. NYC is a county-level source for "NYC", so its state legislative contests match NYC districts only |
| `ny.westchester` | ok, 19 matched (9 confirmed by hand) | Westchester's results are on Enhanced Voting's shared host (`app.enhancedvoting.com/results/public/westchester-county-ny`), so it's configuration. Its state and federal contests, including the 8 Assembly districts, are marked partial |
| `mi.wayne` | ok, 4 matched | Built on election night (`counties/mi.py`). waynecountymi.gov returns 403, but its results are on TotalVote (`michigan.totalvote.com/Wayne`), server-rendered HTML per category. Whole-county districts: MI-13, SD-2, HD-26, HD-27; MI-12, HD-7, HD-8, HD-11 cross county lines and are partial |
| `mi.washtenaw` | ok, 2 matched | Built on election night. `electionresults.ewashtenaw.org/electionreporting/<mon><year>/index.jsp`, one summary table. Bay County posts PDFs only; its two Bay City races aren't on the county report |
| `wi.dane`, `wi.kenosha` | ok, 3 matched | Built on election night (`counties/wi.py`). Dane has a public API (`api.danecounty.gov/api/v1/elections`); Kenosha's results page is `apps.kenoshacounty.org/ElectionResults_v4/?eid=70`. Only districts wholly inside the county stay complete: AD-76 (Dane), AD-64 and AD-65 (Kenosha). The statewide questions and multi-county districts are partial |
| `ny.erie` | ok, 12 matched (Rathi Ravi by hand) | New platform module `platforms/resultscaster.py`, a JSON API under `erie.resultscaster.com/api/resultscasts/`. Erie's Nov 3 election is titled "General Election 2026 test" (slug `testgen`) but holds the real ballot. Onondaga can reuse the module if its site is reachable |

**Probably not on the ballot:**

- **Los Angeles:** Estefany Castañeda (Centinela Valley UHSD), Andrew Yam (Garvey USD) and Alton Wang (Pasadena CCD
  Area 7). Their contests aren't on LA's Nov 3 ballot. California cancels uncontested races and appoints the
  candidate in lieu of election, so these are probably already decided.
- **Orange County:** Tiffany Ackley (Aliso Viejo at-large). The city's Nov 3 races are by district.

**Matching changes:**

- Local races only match contests from their own county, using the `county` column of `results_sources.csv`. This
  stopped "Michael Nguyen" (SF supervisor) from matching an LA city clerk.
- A local race in a county with no source is `no_source`, not `unmatched`.
- A county's copy of a state proposition is marked partial.

**Still to build, on election night** (county, rows, and where results will appear):

| County | Rows | What we know |
|---|---:|---|
| Onondaga | 21 | Results Caster, like Erie: try `platforms/resultscaster.py` with its subdomain |
| Wisconsin: Milwaukee | ~10 (AD 8–21, SD 5, 7) | The county's election-night page has full results but returns 403 to scripts. Manual entries |
| Wisconsin: Racine, Brown, Eau Claire, Douglas | AD 61–63, 90, 93, 73; SD 21, 31 | Racine and Brown post PDFs; the others weren't checked. Several of these districts cross county lines |
| San Diego, Alameda, San Bernardino, San Mateo, Santa Barbara | 16, 15, 10, 12, 7 | Each county's Nov 3 page has no results link yet. Alameda posted June results as PDF/XLSX canvasses |
| San Francisco | 13 | `sfelections.org/results/20261103w/` returns 403 to scripts. Blocked: use manual entries |
| Dutchess, Ulster | 38, 28 | Cumulative PDFs; needs `pdfplumber` |
| Riverside, Kern, Fresno, Tulare; Orange NY, Onondaga, Rockland | | Blocked to scripts (from the source research) |

Until then, the high-priority rows stay with the [manual federal races](#manual-federal-races). New York's state
legislative races outside NYC have no source: the state BOE site (`nyenr.elections.ny.gov`) still returns 403 to
scripts on election night.

**Matching changes on election night:**

- A county-level source (any jurisdiction named "... County", or NYC) covers only some of a state's districts, so its
  contests are skipped by the "same surname, any district" and whole-state fallbacks. This stopped WFP's Patrick
  Carroll (AD-96) from going to review against Robert Carroll (AD-44) in NYC.
- Clarity county contests are now labeled "Travis County", not "Travis", so the county filter applies to them. A
  Travis County utility district race had matched a Tarrant County candidate.
- "Legislature" and "Legislator" count as the same office word.
- Enhanced Voting combines a candidate's party lines into one choice, and county Enhanced Voting sources mark state
  and federal contests partial.
- "Member of Assembly" (Westchester, Erie) is a State Assembly race.

## What the probes found

`scrapers/explore/probe_feeds.py` checked the main state feeds on the evening of Nov 2. Several are already serving
the Nov 3 contests with zero votes, which means parsers and matching can be built and tested against the real
contest lists tonight.

| Feed | Status Nov 2 | What it returns |
|---|---|---|
| California SoS API | **Live, Nov 3 contests loaded** | JSON per office: `api.sos.ca.gov/returns/us-rep/district/all`, `state-senate/…`, `state-assembly/…`, `ballot-measures`, statewide offices |
| Pennsylvania | **Live, Nov 3 configured** (election id 117, type G) | Double-encoded JSON. `GetSummaryData` only returns Governor; the per-office method still needs finding |
| North Carolina | **Live, Nov 3 contests loaded** | One JSON array of every contest/candidate (`results_0.txt`), plus per-county files |
| Utah, Rhode Island (Enhanced Voting) | **Live, Nov 3 configured** | One ~1.5 MB JSON per election with every ballot item, statewide and local |
| Georgia, Washington (Enhanced Voting) | **403** | WA says it's "undergoing final launch preparations"; probably opens on election day. GA also 403 |
| New Mexico, Nebraska (same vendor) | **Live, Nov 3 contests loaded** | CSV exports by office group: `resultsCSV.aspx?text=All&type=FED&map=CTY` |
| Oregon | **Live, Nov 3 configured** | Similar vendor, but exports go through an ASP.NET form (`ResultsExport.aspx`) with statewide, legislative and per-county exports |
| Colorado (Clarity) | Responds; **Nov 3 not posted yet** | `elections.json` lists elections (gzip). The 2024 General is there for testing |
| South Carolina (Clarity) | Responds; **no elections listed** | Empty list |
| Texas | Responds; **Nov 3 not listed yet** | Static JSON per election version: `Federal.json`, `StateWide.json`, `Districted.json`, `Version.json` |
| Connecticut | Site loads; **data path not found yet** | Angular app over static JSON |
| Delaware | **Live** | Static HTML page `GE2026.html` |
| Ohio | **Page now loads** (was Cloudflare-blocked) | API path not found yet |
| New York State, Arizona | **403 (Cloudflare challenge)** | Not usable from scripts |

`scrapers/explore/explore_match_ca.py` tested automatic matching against California's live contest list. It
matched **all 44** California federal, state and statewide-measure endorsements using office type, district number
and candidate surname, and found a real data error on the way. WFP lists Damon Connolly for State Senate District
12, but he's on the District 2 ballot.

## Design principles

The design follows *A Philosophy of Software Design*. In practice that means:

- **Deep modules with small interfaces.** The driver knows one thing about a scraper: `pull()` returns a
  `SourceResult`. URLs, election-ID discovery, file formats, pagination and quirks stay inside the scraper.
- **General-purpose platform modules, thin state modules.** One Enhanced Voting module serves GA, UT, WA and RI, and
  one Clarity module serves CO, SC and about 15 counties. Most state modules are a few lines of configuration.
- **Information hiding.** Only the fetcher knows about HTTP, gzip, retries and politeness. Only the store knows
  file paths and history. Only the matcher knows how WFP rows map to contests.
- **Define errors out of existence.** "Election not published yet", "site blocked" and "no votes yet" are normal
  states, not exceptions. Each source returns a status, so one source failing never stops a run.
- **Pull complexity downward.** Normalizing names, districts and party labels happens once, inside each scraper,
  so everything above it works with one consistent model.
- **Comments for intent.** Each module starts with a docstring covering what it's for and what it hides. Feed
  quirks are commented where they're handled.

## Architecture

```
scrapers/scrape_results.py  (driver CLI)
        │  selects sources from the registry (by state, level, county, id)
        ▼
  elex.registry ──► Source.pull(fetcher) ──► SourceResult (status + normalized contests)
                       │  state modules = config for a platform module
                       ▼
                  elex.platforms.{clarity, enhanced_voting, results_csv, …}
                       │
                  elex.fetch.Fetcher (HTTP, gzip, retries, rate limits, conditional GETs)
        │
        ├─► elex.store      writes data/results/latest/<source>.json (+ history snapshot if changed)
        ├─► elex.match      ties endorsements to contests/choices; maintains data/results/matches.csv
        ├─► elex.publish    writes data/results/wfp_results.json (the dashboard's file)
        └─► elex.runlog     writes logs/results/<run_id>.log and <run_id>.json
```

### Directory layout

```
scrapers/
  scrape_wfp_candidates.py      existing
  scrape_results.py             driver CLI (thin: parse args, call elex.run)
  elex/
    config.py                   election date, paths, defaults
    model.py                    Contest, Choice, Reporting, SourceResult
    fetch.py                    Fetcher
    source.py                   Source base class and status values
    registry.py                 every source, plus selection by state/level/county/id
    run.py                      one run: select → pull (concurrently) → store → match → publish → log
    store.py                    latest/history writes
    match.py                    matcher and review file
    publish.py                  builds wfp_results.json
    runlog.py                   text log + JSON summary
    names.py                    shared normalizing: names, districts, parties, office types
    platforms/
      clarity.py                Clarity ENR (state and county sites)
      enhanced_voting.py        Enhanced Voting JSON API
      results_csv.py            NM/NE vendor CSV exports
    states/                     one module per state source (most are platform config)
      ca.py  pa.py  nc.py  ga.py  ut.py  wa.py  ri.py  nm.py  ne.py
      co.py  sc.py  fl.py  tx.py  or_.py  ct.py  de.py  oh.py  md.py  mn.py  la.py  ar.py  dc.py
      manual.py                 hand-entered results (see Blocked and feed-less states)
    counties/
      ca/  los_angeles.py  san_francisco.py  alameda.py  orange.py  san_diego.py  …
      ny/  westchester.py  erie.py  monroe.py  dutchess.py  ulster.py  nyc.py  …
  explore/                      throwaway experiments (not imported by elex)
tests/
  fixtures/<source>/…           saved feed responses (zero-vote Nov 3 plus past elections with real counts)
  test_<platform or source>.py
```

## Core modules

### `elex.fetch.Fetcher`

```python
fetcher.get(url, *, params=None, expect="json" | "text" | "bytes") -> Response
```

**Hides:** user agent, gzip, timeouts, retries with backoff on 5xx and timeouts, a per-host rate limit (default 1
request at a time and at least 1 second apart), and conditional requests. It remembers `ETag`/`Last-Modified` per
URL, so an unchanged feed costs one cheap round-trip and comes back marked `not_modified`. It records every request
(URL, status, bytes, time) for the run log.

**Behavior on refusal:** a 403 or a challenge page comes back as `Blocked`, and the fetcher doesn't retry it. We
don't try to get around bot protection.

### `elex.source.Source`

The one interface every scraper implements:

```python
class Source:
    id: str          # "ca", "ny.westchester", "manual"
    state: str       # "CA"
    level: str       # "state" | "county"
    title: str       # "California SoS returns API"
    tiers: set[int]  # which priority tiers it can supply (1–4), for --list and planning
    min_interval: int = 0   # seconds; e.g. WA posts once a day, so --watch skips it until due

    def pull(self, fetch: Fetcher) -> SourceResult: ...
```

`SourceResult` has a `status` and the normalized contests:

| Status | Meaning |
|---|---|
| `ok` | Contests parsed (they may all have zero votes) |
| `not_modified` | Feed unchanged since the last pull; the previous contests stay current |
| `not_published` | The Nov 3 election isn't on the site yet (e.g. Colorado tonight) |
| `blocked` | The site refused scripted access |
| `error` | Anything unexpected; the message and traceback go to the log |

Each source finds its own election ID: the Clarity EID, Enhanced Voting `publicElectionId`, PA election id or TX
election id, matched by date from `config.ELECTION_DATE`. Nobody has to paste IDs in on election night.

### `elex.registry`

Lists every source and selects them:
`select(states=None, level="all", counties=None, ids=None) -> list[Source]`. Adding a scraper means adding a
module and one line in the registry.

### `elex.run`

One run: select sources, pull them concurrently (a thread pool of 8, with the fetcher's per-host limits), then
store, match, publish and log. It catches every source's exception, so the run always finishes and reports. With
`--watch`, the driver calls `run` in a loop.

### `elex.store`

Writes `data/results/latest/<source>.json` atomically (temp file, then rename). It writes a history snapshot only
when the parsed contests actually changed, compared by content hash, so a night of polling doesn't pile up
identical files. It's the only module that knows these paths.

### `elex.match` and `elex.publish`

See [Matching](#matching-results-to-endorsements) and the [data contract](#data-contract-for-the-dashboard).

### `elex.runlog`

Gives each run a `run_id`, the UTC start time as `20261103T031502Z`. It writes `logs/results/<run_id>.log` (readable:
one line per request, per-source outcome, match changes) and `logs/results/<run_id>.json` (the summary in
[Files, history and logs](#files-history-and-logs)). The candidate scraper will use the same module and log to
`logs/candidates/`, so every data pull is logged.

## The normalized result model

Every scraper converts its feed into this shape. The rest of the system never sees a raw feed.

```json
{
  "source": "ca",
  "contest_id": "state-senate/2",
  "office_type": "state_senate",
  "district": "2",
  "title": "State Senate District 2",
  "jurisdiction": "California",
  "scope": "complete",
  "vote_for": 1,
  "reporting": {"units_reporting": 0, "units_total": 812, "pct": 0.0, "text": "0% (0 of 812) precincts reporting"},
  "feed_updated_at": "2026-11-02T18:28:00-08:00",
  "choices": [
    {"choice_id": "Damon Connolly", "name": "Damon Connolly", "party": "DEM", "votes": 0, "pct": 0.0,
     "party_lines": null}
  ]
}
```

- `office_type` is a fixed list that mirrors `office_category`: `federal_senate`, `federal_house`, `governor`,
  `lt_governor`, `attorney_general`, …, `state_senate`, `state_house`, `measure`, `local`, `judicial`. Each scraper
  maps its own labels to this list in one place.
- `scope` is `complete` when the source reports the whole contest, and `partial` when it reports only one county's
  share (NY counties reporting a multi-county Assembly district, NJ counties reporting a U.S. House district). Partial
  contests matter for New York (see [Blocked and feed-less states](#blocked-and-feed-less-states)).
- `party_lines` holds per-line votes where a feed gives them (NY fusion voting, e.g. `{"DEM": 9100, "WOR": 1400}`).
  WFP-line totals are worth capturing when they're available.
- Measures use the choices `Yes` and `No` (or the feed's labels mapped to them).

## Matching results to endorsements

**Goal:** tie each row of `data/candidates.json` to one contest and one choice, without anyone hand-mapping
1,216 rows, while keeping every uncertain match visible for review.

**How it matches,** in order:

1. **Measures:** the measure number or letter from the WFP name ("Prop 39", "Issue 8", "Question 9", "Amendment
   3C"), matched within the right jurisdiction. The matched choice is WFP's `position` (`Yes` or `No`); WFP opposes
   several measures, such as CA Props 39 and 41–45.
2. **Candidates:** same `office_type` and the same district number, then surname match (accents folded, so "Rascón"
   matches "Rascon"). The district number is the last number in the office text, which handles WFP's typos like
   "Distrcit 6".
3. **Fallback:** if the listed district has no candidate with that surname, search every contest of that office
   type. A hit is recorded as `needs_review` with the reason "district differs from WFP listing" (the Connolly case).
4. **Ambiguity:** two possible matches, or a surname shared by several candidates in one contest, is recorded as
   `needs_review` and not guessed.

**The review file** is `data/results/matches.csv`, one row per endorsement:

| Column | Example |
|---|---|
| `wfp_id`, `name`, `office` | `93`, `Damon Connolly`, `State Senate, District 12` |
| `source`, `contest_id`, `choice_id` | `ca`, `state-senate/2`, `Damon Connolly` |
| `method` | `measure_number`, `district_surname`, `surname_any_district`, `manual` |
| `status` | `auto`, `needs_review`, `confirmed`, `unmatched`, `not_on_ballot` |
| `note` | `district differs from WFP listing (SD 12 → SD 2)` |

**How it's reviewed:** you edit `status` to `confirmed` or fix the IDs and set `method` to `manual`. The matcher
never changes `confirmed` or `manual` rows; it re-evaluates everything else each run. Rows with `nov3_ballot = no` in
`results_sources.csv` are `not_on_ballot` and never matched.

**Do this tonight.** CA, NC, NM, NE, PA, UT and RI already list their Nov 3 contests. Running the matcher before
polls close means most matches can be reviewed before any votes come in.

## Data contract for the dashboard

The dashboard reads one file, `data/results/wfp_results.json`, built by `elex.publish` at the end of every run from
the latest source files and `matches.csv`.

```json
{
  "election_date": "2026-11-03",
  "generated_at": "2026-11-04T05:12:44Z",
  "run_id": "20261104T051230Z",
  "sources": {
    "ca": {"status": "ok", "fetched_at": "2026-11-04T05:12:31Z", "feed_updated_at": "2026-11-03T21:10:00-08:00"}
  },
  "results": {
    "93": {
      "status": "counting",
      "source": "ca",
      "contest": "State Senate District 2",
      "reporting": {"pct": 41.2, "text": "41.2% (335 of 812) precincts reporting"},
      "updated_at": "2026-11-03T21:10:00-08:00",
      "wfp_choice": "Damon Connolly",
      "wfp_leading": true,
      "choices": [
        {"name": "Damon Connolly", "party": "DEM", "votes": 81234, "pct": 61.8, "is_wfp": true},
        {"name": "Tief Gibbs", "party": "REP", "votes": 50213, "pct": 38.2, "is_wfp": false}
      ],
      "match_status": "confirmed"
    }
  }
}
```

**`status` values for each endorsement:**

| Status | Meaning |
|---|---|
| `awaiting` | Matched; no votes counted yet |
| `counting` | Votes are coming in |
| `final` | The source marks results certified/official (set per source when that's published) |
| `not_on_ballot` | `nov3_ballot = no` (decided earlier, or never qualified) |
| `no_source` | No scraper covers it yet (blocked, feed-less, or not built) |
| `unmatched` | A source covers it, but matching failed; see `matches.csv` |

**We don't call races.** The file reports votes, percentages, reporting status and `wfp_leading`. Whether and how
to show "projected" outcomes is a dashboard decision, and unofficial counts shift for days in CA, WA and OR.

## Command-line interface

`scrapers/scrape_results.py` has four subcommands. `run` is the default.

```
python3 scrapers/scrape_results.py [run] [options]
python3 scrapers/scrape_results.py list  [--states …] [--level …]
python3 scrapers/scrape_results.py match [--states …]
python3 scrapers/scrape_results.py manual-template [--force]
```

**`run`: pull, store, match, publish, log**

| Option | Default | Meaning |
|---|---|---|
| `--states CA,PA,NY` | all | Two-letter codes, comma-separated (`DC` included) |
| `--level state\|county\|all` | `all` | Statewide sources, county sources, or both |
| `--counties "CA:Los Angeles,NY:Erie"` | — | Only these county sources (implies `--level county`) |
| `--sources ca,ny.erie` | — | Exact source IDs, for debugging one scraper |
| `--watch MINUTES` | off | Repeat every N minutes until Ctrl-C; each pull is its own run with its own log |
| `--dry-run` | off | Fetch, parse and match, but write nothing to `data/` (logs are still written) |
| `--no-publish` | off | Update `latest/` and history, but leave `wfp_results.json` alone |
| `-v`, `--verbose` | off | Echo the full log to the terminal; otherwise one line per source plus a summary |

**`list`:** prints every registered source with its state, level, tiers, platform and current state (built, last
status, last run time). It makes no network requests.

**`manual-template`:** writes `data/results/manual_entries.csv` pre-filled for the
[manual federal races](#manual-federal-races). It won't overwrite a file that has votes in it unless you pass `--force`.

**`match`:** re-runs matching and publishing from `latest/` without fetching. Use it after editing `matches.csv`.

**Exit codes:** `0` if every selected source returned `ok`, `not_modified` or `not_published`. `1` if any returned
`blocked` or `error`. `2` for bad arguments.

**Examples**

```bash
python3 scrapers/scrape_results.py                              # everything
python3 scrapers/scrape_results.py --states CA                  # California: state API + all CA counties
python3 scrapers/scrape_results.py --states CA --level state    # just the CA SoS API
python3 scrapers/scrape_results.py --states NY --level county   # every NY county scraper
python3 scrapers/scrape_results.py --counties "CA:Los Angeles"  # one county
python3 scrapers/scrape_results.py --states CA,PA,NC --watch 5  # election night polling
python3 scrapers/scrape_results.py --dry-run --sources ut -v    # debug one scraper
```

`--tiers` is left out on purpose. Every feed returns all of its contests at once, so filtering by tier at run time
saves nothing. Tiers drive build order, and `list` shows them.

## Files, history and logs

```
data/results/
  latest/<source>.json                     newest normalized contests per source (+ status, fetched_at)
  history/<source>/<run_id>.json           snapshot, written only when contests changed
  matches.csv                              review file (hand-edited rows are preserved)
  manual_entries.csv                       hand-entered results (see Manual federal races)
  wfp_results.json                         the dashboard's file
logs/
  results/<run_id>.log                     readable run log
  results/<run_id>.json                    run summary
  candidates/<run_id>.log, .json           candidate scraper runs
```

**Run summary (`<run_id>.json`):**

```json
{
  "run_id": "20261104T051230Z", "command": "run --states CA,PA --watch 5", "duration_s": 14.2,
  "sources": {
    "ca": {"status": "ok", "contests": 171, "changed": true, "requests": 6, "bytes": 412331, "seconds": 3.1},
    "co": {"status": "not_published"}
  },
  "matching": {"auto": 812, "confirmed": 140, "needs_review": 9, "unmatched": 31, "not_on_ballot": 12},
  "errors": []
}
```

**Size:** contests normalized from every state feed come to a few MB per snapshot. History is only written on
change, so a night of 5-minute polling should stay in the tens of MB. I'd suggest git-ignoring `logs/` and
`data/results/history/` and committing `latest/`, `matches.csv` and `wfp_results.json`. That's your call, since you
manage commits.

## Scraper catalog

"Rows" counts WFP endorsements the source covers, excluding the 12 not on the Nov 3 ballot. Tier columns follow your
priority order: T1 federal, T2 state offices, T3 statewide measures, T4 local.

### Platform modules (general-purpose)

| Module | How it works | Used by |
|---|---|---|
| `platforms/enhanced_voting.py` | `api/jurisdictions/<j>` → find the `publicElectionId` by date → `api/elections/<j>/<id>/data` (one JSON: `ballotItems[]` → `summaryResults.ballotOptions[].voteCount`, `reportingStatus`). Local ballot items are in the same file | GA, UT, WA, RI |
| `platforms/clarity.py` | `<site>/elections.json` (gzip) → EID by date → `<EID>/current_ver.txt` → `<EID>/<ver>/json/en/summary.json`. Uses the version number for change detection. `detailxml.zip` (county breakdown) only if needed | CO (state + county sub-sites), SC, FL mirror; counties: Santa Clara, Contra Costa, Sonoma, Marin, Ventura (CA); Travis, Dallas, Tarrant, Bexar, Denton (TX); Hudson, Middlesex, Essex (NJ); Hamilton (OH) |
| `platforms/results_csv.py` | `ResultsMedia.aspx` lists export types → `resultsCSV.aspx?text=All&type=<T>&map=CTY` per type (`FED`, `STATE`, `SW`, county/municipal types). Columns: race, candidate, party, votes, precincts reporting | NM, NE |

### State sources

| Source | Feed | Election ID | Rows (T1/T2/T3/T4) | Phase | Notes |
|---|---|---|---|---|---|
| `ca` | CA SoS returns API (JSON) | none needed | 7/24/13/0 | 1 | Verified tonight. Statewide offices, Congress, legislature, BOE, props. No local races. Counting runs ~30 days |
| `pa` | `electionreturns.pa.gov/api/ElectionReturn` | `GetAllElections` → id 117, type G | 4/39/0/0 | 1 | Double-encoded JSON. **Discovery:** the per-office method (summary only returns Governor). Inspect the site's own requests in a browser |
| `nc` | `er.ncsbe.gov/enr/20261103/data/results_0.txt` | date in path | 1/4/0/4 | 1 | One file, every contest, including DA and Supreme Court. Local rows come free |
| `ut`, `ri` | Enhanced Voting | `General11032026`, `2026StatewideGeneralElection` | UT 0/4/0/2, RI 0/6/0/9 | 1 | Verified tonight. Providence and Salt Lake County included |
| `ga`, `wa` | Enhanced Voting | by date | GA 1/27/0/3, WA 1/12/0/4 | 1 | 403 tonight (WA "launch preparations"). Same module, so they work the moment the sites open; otherwise `blocked` |
| `nm`, `ne` | `results_csv` platform | current election only | NM 1/31/0/6, NE 0/0/0/3 | 1 | Verified tonight. NM county commission races are in the CSVs |
| `co` | Clarity (state + county sub-sites) | by date, from `elections.json` | 1/30/14/40 | 2 | Nov 3 EID not posted yet. County sub-sites cover local races and measures |
| `sc` | Clarity | by date | SC 1/4/0/0 | 2 | SC lists no elections yet |
| `fl` | FL results file | Downloads page link | FL 1/0/0/0 | 2 | Rebuilt on election night: the Clarity mirror never posted Nov 3. `states/fl.py` reads the tab-delimited file linked from floridaelectionwatch.gov's Downloads page (the plain file URL serves a stale cached copy) and sums county rows. U.S. Senate (Nixon) only |
| `tx` | `results.texas-election.com/static/data/election/<id>/<ver>/{Federal,StateWide,Districted}.json` | discover via `Home.json`/`Lookups.json` | 0/3/0/0 | 2 | Nov 3 not listed yet. Local rows go to TX county Clarity sites |
| `or_` | `results.oregonvotes.gov` exports (`ResultsExport.aspx` form) or `ResultsAjax.svc` | current election | 3/33/0/44 | 2 | **Discovery:** the export is an ASP.NET postback. Per-county exports may cover OR's 44 local rows |
| `ct` | `ctemspublic.tgstg.net` static JSON | discover | 1/81/0/0 | 2 | **Discovery:** data path. 81 State House/Senate rows, so a high payoff |
| `de` | `elections.delaware.gov/results/enr/GE2026.html` | fixed URL | 0/12/0/1 | 2 | HTML table parsing |
| `oh` | `liveresults.ohiosos.gov` | discover | 2/18/1/0 | 2 | Page loads now; **discovery:** API path. Treat as best-effort |
| `md`, `mn`, `la`, `ar`, `dc` | CSV/HTML (MD), delimited text (MN), JSON blobs (LA), TotalResults API (AR), JSON (DC) | per source | MD 0/1/0/8, others ≤2 rows | 2 | Small row counts; mostly local races that come free with the state feed |
| `nj` | NJ county Clarity sites | via Clarity | 2/0/0/6 | 2 | U.S. House districts span counties, so the results are `partial` and need summing (see below) |
| `manual` | `data/results/manual_entries.csv` | n/a | any | 1 | Hand-entered results for federal races with no working scraper (see Manual federal races) |

### County sources (Phase 3: CA and NY first)

**California** (190 local rows):

| Source | Feed | Rows | Notes |
|---|---|---|---|
| `ca.los_angeles` | `results.lavote.gov` (JSON) | 29 | Largest CA county; LA Superior Court races |
| `ca.orange`, `ca.san_diego`, `ca.alameda`, `ca.san_francisco`, `ca.san_mateo`, `ca.san_bernardino`, `ca.santa_barbara`, `ca.santa_cruz`, `ca.sacramento`, `ca.stanislaus`, `ca.solano` | County HTML/TXT pages | 2–21 each | Alameda and SF publish ranked-choice rounds separately (Oakland, Berkeley, SF) |
| `ca.santa_clara`, `ca.contra_costa`, `ca.sonoma`, `ca.marin`, `ca.ventura` | Clarity platform | 1–12 each | Configuration only |
| Riverside, Kern, Fresno, Tulare | Blocked to scripts | 11, 5, 4, 4 | Phase 4 / manual |

**New York** (250 local rows):

| Source | Feed | Rows | Notes |
|---|---|---|---|
| `ny.westchester`, `ny.erie`, `ny.monroe`, `ny.putnam`, `ny.nassau`, `ny.schenectady`, `ny.cattaraugus`, `ny.chemung` | County HTML results | 1–20 each | Verified in research |
| `ny.dutchess`, `ny.ulster` | Cumulative PDFs | 38, 28 | Needs `pdfplumber`. Dutchess posts slowly into the next day |
| `ny.broome`, `ny.oneida`, `ny.chautauqua`, `ny.niagara` | PDF/XLS/HTML, vendor portal (Niagara) | 8–14 each | Unverified URLs |
| `ny.nyc` | NYC BOE (`vote.nyc` results pages) | 1 local (Civil Court), plus NYC's state legislative and congressional districts | **Discovery.** It may be the main route to NYC's state legislative races (see below) |
| Orange, Onondaga, Rockland, Cayuga, Tompkins | Blocked or didn't load | 18, 21, 6, 1, 1 | Phase 4 / manual |

**Other counties** (Phase 4, 65 rows): Oregon, Texas, New Jersey, Ohio (Franklin), Michigan (Washtenaw, Bay), and Wyoming
(Albany).

## Phases and coverage

Counts are WFP endorsements on the Nov 3 ballot (1,204 of 1,216).

| Phase | When | Scope | T1 | T2 | T3 | T4 | Total |
|---|---|---|---:|---:|---:|---:|---:|
| **1** | Nov 2 night – Nov 3 evening | Core modules, matching, data contract; `ca`, `pa`, `nc`, Enhanced Voting (`ut`, `ri`, `ga`, `wa`), `nm`, `ne`, `manual`; candidate scraper logging | 15 | 147 | 13 | 31 | **206** |
| **2** | Nov 3 night – Nov 6 | `co`, `sc`, `fl`, `tx`, `or_`, `ct`, `de`, `oh`, `md`, `mn`, `la`, `ar`, `dc`, `nj` | 12 | 183 | 15 | 59 | **269** |
| **3** | Nov 4 – Nov 13 | CA and NY county scrapers; partial-contest summing for NY legislative and congressional districts | 0 | 0 | 0 | 432 | **432** |
| **4** | Through certification | Other counties; certified-results files for blocked/feed-less states; `final` status | 0 | 0 | 0 | 65 | **65** |
| Blocked / no feed | — | NY State ENR, AZ, KY, TN; feed-less MA, MI, WI, ME | 22 | 194 | 14 | 2 | **232** |

**Phase 1 in more detail,** in build order:

1. `requirements.txt` and virtualenv; `config`, `model`, `fetch`, `source`, `registry`, `runlog`, `store`.
2. `run` and the driver CLI with `run`/`list`, tested end-to-end with the `manual` source.
3. `ca` (verified feed, 44 rows to test matching on) and `match` + `publish`. Run matching tonight and review
   `matches.csv`.
4. `manual-template`, and fill in `manual_entries.csv` for the [manual federal races](#manual-federal-races).
5. `platforms/enhanced_voting` + `ut`, `ri` (then `ga`, `wa` with no extra code).
6. `nc`, then `platforms/results_csv` + `nm`, `ne`.
7. `pa`, once its per-office method is found (43 rows, so worth the discovery time).
8. Candidate scraper logging via `runlog`.

If time runs short on Nov 3, steps 1–5 are the minimum useful set: 41 federal/state rows (82 if Georgia and
Washington open their sites), plus CA props, RI/UT local races, and every remaining federal race by hand. With the
manual entries, all 49 federal endorsements are covered on election night.

## Blocked and feed-less states

232 endorsements have no scrapeable official source on election night. The biggest gap is **New York's 140 federal
and state legislative races**, because the state's ENR site is behind a Cloudflare challenge. We won't try to get
around it. The plan instead:

1. **New York via counties (Phase 3).** NY county boards publish every contest on their ballot, including the county's
   share of congressional and legislative districts. County scrapers record those contests with `scope: partial`.
   A small aggregation step in `publish` sums partials for a district once every county in that district has
   reported. It needs a district → county list, a small static file built once from the state's district maps.
   Districts wholly inside one county, which covers most NYC and many upstate seats, are complete from a single
   county. NYC is the key piece: `ny.nyc` would cover a large share of the 140 rows.
2. **Manual entries (Phase 1).** `manual_entries.csv` lets a person enter results read from any public page:
   source URL, time, contest, choices, votes, reporting. The `manual` source treats them like any other feed, so they
   flow through matching and publishing. On Nov 3 that means every federal race without a working scraper; see
   [Manual federal races](#manual-federal-races) below.
3. **Certified results (Phase 4).** MA (PD43+), MI, WI and ME publish official canvass files days or weeks later.
   Those are easy to scrape and give every blocked state `final` results eventually.
4. **Ask (deferred).** Some blocked agencies (NY BOE, AZ SoS) offer media or data feeds on request. We're holding
   off for now; worth revisiting if the county route for New York falls short.

### Manual federal races

Every federal endorsement that has no working scraper on election night is entered by hand. That's 34 of the 49
federal endorsements, or 36 if Georgia's and Washington's sites stay closed.

| Why it's manual | State | Races |
|---|---|---|
| No scrapeable source on election night | Michigan (4) | U.S. Senate (El-Sayed); House 7 (Lawrence), 12 (Tlaib), 13 (McKinney). Results come from 83 county clerks; the state posts only after all have reported |
| | New York (15) | House 1, 2, 7, 10, 13, 14, 17, 18, 19, 20, 22, 23, 24, 25, 26. The state ENR site is blocked to scripts but readable in a browser |
| | Kentucky, Maine, Tennessee, Ohio (5) | KY and ME U.S. Senate (Booker, Jackson); TN House 9 (Pearson); OH House 7 and 8 (Poindexter, Enoch) |
| Scraper not built until Phase 2 | Florida (1) | U.S. Senate (Nixon) |
| | Colorado, Connecticut, DC, New Jersey, Oregon, South Carolina (9) | CO 1 (Kiros), CT 5 (Hayes), DC delegate (White), NJ 10 and 11 (McIver, Mejia), OR U.S. Senate (Merkley) and House 1 and 4 (Bonamici, Hoyle), SC 4 (McClain) |
| Only if the site stays blocked | Georgia, Washington (2) | GA 1 (Hollowell), WA 7 (Jayapal) |

**How entry works.** `scrape_results.py manual-template` writes `manual_entries.csv` with one row per manual race,
already filled in with the contest and the WFP candidate. You add a row for each opponent once, then update votes and
reporting from the official page as the night goes on, and run `match` (or let the next `run` pick it up).

| Column | Example |
|---|---|
| `contest_id` | `mi.us-senate` (one ID per race; every candidate row in the race shares it) |
| `state`, `office`, `district` | `MI`, `U.S. Senate`, blank |
| `choice`, `party` | `Abdul El-Sayed`, `DEM` |
| `votes` | `1204331` |
| `reporting_pct` | `62` (blank if the page doesn't say) |
| `source_url`, `as_of` | the page you read, and the time on it (or the time you read it) |

**When a scraper and a manual entry both have a race,** the scraper wins: `publish` uses manual results only for
endorsements no scraped source matched. So when `fl`, `co` and the other Phase 2 scrapers come online, their races
move off the manual list on their own, and the manual rows stay as a fallback if a scraper breaks. NY's House races
move to the county scrapers in Phase 3 the same way.

**Workload.** About 34 races of two to four candidates each. Entering every race on every update isn't realistic, so
the runbook updates them on each dashboard rebuild, not on each poll.

## Testing

- **Fixtures from real feeds.** Save each source's Nov 2 zero-vote response (the real Nov 3 contest list) and a past
  election with real counts from the same platform: CO Clarity 2024 General (EID 122598), NC `enr/20241105`, PA 2024
  general, UT/RI 2024–25 Enhanced Voting elections. Parser tests run offline against them.
- **Matcher tests:** the cases found so far: Connolly's district, typo'd districts ("Distrcit"), "Sate Assembly",
  measure numbers with dashes ("Prop – 1"), "No" positions, accents, nicknames ("Nicholas \"Nick\" Schultz").
- **End-to-end:** `run --dry-run` against live feeds tonight, checking statuses, contest counts and match rates in
  the run summary.
- `pytest`, run with `python3 -m pytest`.

Everything runs on your machine. Keep it plugged in and stop it from sleeping, since `--watch` stops when the
laptop does.

1. **Before 7pm ET:** re-scrape candidates (WFP's list keeps changing) and log the differences in
   [candidate-changes.md](candidate-changes.md). Then run `match` and clear `needs_review` rows. Run
   `manual-template` and add the opponents for each manual race.
2. **From 7pm ET:** `scrape_results.py --watch 5` in one terminal. Watch the one-line-per-source output. A `blocked`
   or `error` doesn't stop the loop.
3. **Each dashboard update** (every 30–60 minutes is a reasonable pace):
   1. Update `manual_entries.csv` from the official pages for the manual federal races.
   2. Run `scrape_results.py match` so `wfp_results.json` includes the manual entries.
   3. Rebuild the dashboard, then commit and push.
4. **Every hour or so:** `list` to see which sources moved from `not_published` to `ok` (CO, SC, FL, GA and the TX
   and NJ county sites are the ones to watch). Check the latest summary in `logs/results/` for new `unmatched` rows.
5. **Late night:** switch to `--watch 15`. CA, WA and OR count for days, so daily runs and rebuilds after Nov 4 are
   enough.

Since the dashboard only changes when you rebuild, polling faster than every 5 minutes buys nothing. The polls between
rebuilds still matter: they fill the history and catch a source breaking before the next rebuild.

## Resolved and open questions

Answered Nov 2:

1. **How will the dashboard get updates?** You rebuild it and push a commit for each update. The dashboard keeps
   bundling JSON at build time and imports `data/results/wfp_results.json`. Each update's commit only needs that file
   (and `matches.csv` if you changed it), so git-ignoring `logs/` and `data/results/history/` keeps those commits small.
2. **Where should the scrapers run on election night?** On your machine. Nothing in the design ties it to one host, so
   a scheduled GitHub Action can be added later if it's useful.
3. **Should we ask NY BOE and AZ SoS for media feeds?** Not yet.
4. **Which races get manual entries?** Michigan, Florida, and every other federal race without a working scraper on
   election night: 34 races (36 if GA and WA stay blocked). See [Manual federal races](#manual-federal-races).

Still open:

5. **Data issue found:** WFP lists Damon Connolly (CA) for State Senate District 12; he's on the District 2 ballot.
   The matcher handles it. You're looking into it; it's also worth noting in
   [election-results-sources.md](election-results-sources.md), and WFP may want to know.
