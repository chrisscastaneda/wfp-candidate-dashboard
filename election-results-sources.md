# Election Results Sources: Nov 3, 2026 General

Where to pull live and final results for every WFP endorsement in `candidates.json`
(1,194 rows: 1,129 candidates + 65 ballot measures, across 31 states + DC; scraped Nov 2, 2026).
Research done Nov 1–2, 2026. Each source below was loaded and inspected unless marked otherwise.

The per-race mapping is in [`results_sources.csv`](results_sources.csv): one row per endorsement, with its source, URL,
data endpoint, format, and flags. Column definitions are at the bottom of this doc.

## Key findings

1. **Most states do have a machine-readable feed, even without a documented API.** Their results websites load
   JSON behind the scenes. 23 of the 32 jurisdictions have a JSON/XML/text feed that can be polled directly. Only a few
   are true dead ends on election night (MA, MI, WI, ME).
2. **A handful of shared platforms cover a large share of the work.** One integration per platform, reused:
   - **Enhanced Voting** (identical JSON API): Georgia, Utah, Washington, Rhode Island. Each also exposes county/city
     localities, so local races come along for free.
   - **Clarity ENR** (standard `summary.json` + `detailxml.zip`): Colorado statewide plus every Colorado county,
     South Carolina, Florida (mirror), and 14 relevant counties: Contra Costa, Santa Clara, Sonoma, Marin, Ventura (CA);
     Travis, Dallas, Tarrant, Bexar, Denton (TX); Hudson, Middlesex, Essex (NJ); Hamilton (OH).
   - **Same vendor, same layout**: Nebraska and New Mexico.
3. **Local races are the hard part: 502 rows depend on ~60 county offices.** New York (249 rows across 30 counties) and
   California (186 rows across 21 counties) dominate. NY counties mostly post HTML/PDF summaries, often slowly.
4. **Four states have no usable official election-night source**: Massachusetts (the Secretary does not publish
   unofficial results), Michigan (county clerks only; state posts ~24h later), Wisconsin (72 county clerks; WEC doesn't
   compile), and Maine (slow spreadsheets; U.S. Senate is ranked-choice). Use AP or Decision Desk HQ there (64 rows, counting Kentucky's one U.S. Senate race, which is simpler via AP).
5. **Several feeds are already live for Nov 3**: California API, North Carolina, Nebraska, New Mexico, Utah,
   Washington, Rhode Island, Louisiana, Delaware, Connecticut, Kentucky, Arkansas, plus Denton and Hamilton counties on
   Clarity. Still pending (as of Nov 1): Colorado, Georgia, Texas, and DC haven't posted their Nov 3 election IDs.
6. **10 endorsements are not on the Nov 3 ballot.** Their races were decided earlier in 2026: Newark mayor (May 12),
   Denton city council (May 2 and June 13), Newburgh and Eastchester school boards (May 19), and Fairport village
   (March 18). The `nov3_ballot` column marks them `no`, with the date and outcome. Show them as decided rather than
   waiting for Nov 3 results. Another 5 rows are still `unconfirmed` (see below).

## Coverage summary

| How results are reached | Rows | Notes |
|---|---:|---|
| State source, state/federal races | 597 | Includes 64 rows in MA/MI/WI/ME/KY where AP is recommended |
| State source also covers the local race | 48 | DC, MD, MN, NE, NC, RI, GA, UT, WA, DE, LA, AR, AZ |
| County sub-sites under the state Clarity (Colorado) | 40 | Same platform as statewide |
| Separate county/city source | 508 | ~60 county offices, mostly NY and CA |
| County not yet identifiable | 1 | "Charlestown Town Council" (NY) |

By URL status: 809 rows point to a source verified working, 292 to a source that exists but blocks scripted requests
(Cloudflare/Akamai; needs a real browser or browser-like client), 92 to a URL found in research but not loaded,
and 1 row has no source yet.

## State-by-state sources

Rows = WFP endorsements in that state. "Live" = updates through election night.

| State | Rows | Official source | Data access | Live | Local races? | Notes |
|---|---:|---|---|---|---|---|
| Arizona | 23 | [results.arizona.vote](https://results.arizona.vote/) | JSON from `cdn1.arizona.vote/data/<election>/…` | Yes | County view | Cloudflare. Phoenix backup: [Maricopa County](https://elections.maricopa.gov/results-and-data/election-results.html) |
| Arkansas | 1 | [arkansas.tally-enr.com](https://arkansas.tally-enr.com/) | JSON API `enr-results-api.totalresults.com` | Yes | Yes | 2026 General already configured |
| California | 234 | [electionresults.sos.ca.gov](https://electionresults.sos.ca.gov/) | **JSON API** `api.sos.ca.gov/returns/<office>[/district/all]` | Yes | No | Already serving Nov 3 candidates. Counting runs ~30 days |
| Colorado | 85 | [Clarity ENR – CO](https://results.enr.clarityelections.com/CO/) | Clarity `summary.json` / `detailxml.zip`; county EIDs in `electionsettings.json` | Yes | Yes (county sub-sites) | Nov 3 EID not posted yet |
| Connecticut | 82 | [CT Election Center](https://ctemspublic.tgstg.net/#/home) | Static JSON `ng-app/data/election/<id>/<id>/*_Electiondata.json` | Partial | Yes | Nov 2026 election listed. Towns report on their own schedule. (`ctemspublic.ct.gov` didn't resolve) |
| Delaware | 13 | [GE2026 results](https://elections.delaware.gov/results/enr/GE2026.html) | HTML | Yes | Yes | Page already linked |
| DC | 8 | [electionresults.dcboe.org](https://electionresults.dcboe.org/) | JSON + SignalR push | Yes | Yes | First general with RCV; Nov 2026 not listed yet |
| Florida | 1 | [results.elections.myflorida.com](https://results.elections.myflorida.com/) | HTML/TXT; Clarity mirror | Yes | — | U.S. Senate only |
| Georgia | 31 | [results.sos.ga.gov](https://results.sos.ga.gov/results/public/Georgia) | **Enhanced Voting** `/results/public/api/elections/Georgia/<id>/data` | Yes | Yes | Nov 3 election not configured yet |
| Kentucky | 1 | [vrsws.sos.ky.gov/liveresults](https://vrsws.sos.ky.gov/liveresults/) | HTML | Yes | — | Akamai. AP simpler for one race |
| Louisiana | 1 | [voterportal.sos.la.gov/graphical](https://voterportal.sos.la.gov/graphical) | JSON blobs `ElectionResults/Data?blob=20261103/…` | Yes | Yes (parish) | Nov 3 files staged |
| Maine | 2 | maine.gov SoS results | XLSX/PDF, posted later | No | — | **Use AP.** U.S. Senate is ranked-choice |
| Maryland | 9 | [elections.maryland.gov/elections/2026](https://elections.maryland.gov/elections/2026/index.html) | HTML/CSV (expected at `general_results/`) | Yes | Yes | Covers county council, state's attorney, sheriff, exec |
| Massachusetts | 20 | none on election night | AP; certified later on [PD43+](https://electionstats.state.ma.us/) | No | — | **Use AP** |
| Michigan | 19 | county clerks; [state page](https://www.michigan.gov/sos/elections/election-results-and-data) later | AP / county sites | Partial | County | **Use AP** for state/federal |
| Minnesota | 2 | [electionresults.sos.mn.gov](https://electionresults.sos.mn.gov/) | Delimited text downloads | Yes | Yes | County attorney races included |
| Nebraska | 3 | [electionresults.nebraska.gov](https://electionresults.nebraska.gov/) | HTML + `ResultsMedia.aspx` exports | Yes | Yes | Nov 3 configured |
| New Jersey | 8 | county clerks (Clarity) | Clarity per county | Yes | County | Multi-county U.S. House districts need summing or AP |
| New Mexico | 11 | [electionresults.sos.nm.gov](https://electionresults.sos.nm.gov/) | HTML + `ResultsMedia.aspx` exports | Yes | Yes | Nov 3 configured |
| New York | 390 | [nyenr.elections.ny.gov](https://nyenr.elections.ny.gov/) | HTML (ASP.NET) | Yes | **No** | Federal/state/legislative only. Local: 30 county boards |
| North Carolina | 9 | [er.ncsbe.gov](https://er.ncsbe.gov/) | **JSON** `enr/20261103/data/results_0.txt` + per-county files | Yes | Yes | Already live; every contest incl. DA and Supreme Court |
| Ohio | 27 | [liveresults.ohiosos.gov](https://liveresults.ohiosos.gov/) | JSON `Api/v1/Contest/*` | Yes | No | Cloudflare. Local: Hamilton (Clarity), Franklin |
| Oregon | 80 | [results.oregonvotes.gov](https://results.oregonvotes.gov/) | HTML | Partial | No | Live at 8pm Nov 3; mail counting runs 1–2 weeks. Local: counties |
| Pennsylvania | 43 | [electionreturns.pa.gov](https://www.electionreturns.pa.gov/) | **JSON API** `api/ElectionReturn/*` | Yes | — | Counties upload in batches |
| Rhode Island | 15 | [electionresults.ri.gov](https://electionresults.ri.gov/results/public/rhodeisland) | **Enhanced Voting** JSON | Yes | Yes | Nov 3 configured; Providence and East Providence included |
| South Carolina | 5 | [Clarity ENR – SC](https://results.enr.clarityelections.com/SC/) | Clarity | Yes | Yes | |
| Tennessee | 5 | [tnelectionresults.com](https://www.tnelectionresults.com/home) | HTML | Yes | Yes | Blocks scripts; works in a browser |
| Texas | 11 | [results.texas-election.com](https://results.texas-election.com/) | Static JSON `static/data/election/<id>/…` | Yes | No | Still shows 2024 (Nov 1). County races: 5 county Clarity sites |
| Utah | 6 | [electionresults.utah.gov](https://electionresults.utah.gov/results/public/Utah) | **Enhanced Voting** JSON | Yes | Yes | Nov 3 configured; Salt Lake County included |
| Washington | 17 | [results.votewa.gov](https://results.votewa.gov/results/public/washington) | **Enhanced Voting** JSON | Partial | Yes | Nov 3 configured. Daily updates for ~2 weeks |
| Wisconsin | 26 | 72 county clerks ([list](https://elections.wi.gov/wisconsin-county-election-websites)) | AP / county PDFs | Partial | County | **Use AP**; legislative districts cross counties |
| Wyoming | 1 | Albany County Clerk | HTML/PDF | Partial | County | |

## County sources for local races

Ordered by number of WFP rows. Clarity counties expose the same JSON/XML as statewide Clarity sites.

| County | Rows | Source | Format | Status |
|---|---:|---|---|---|
| Dutchess, NY | 38 | [elections.dutchessny.gov](https://elections.dutchessny.gov/) | PDF, posts slowly into next day | verified |
| Los Angeles, CA | 29 | [results.lavote.gov](https://results.lavote.gov/) | JSON/HTML | verified |
| Ulster, NY | 28 | [elections.ulstercountyny.gov](https://elections.ulstercountyny.gov/) | Cumulative PDF + HTML | verified |
| Orange, CA | 21 | [ocvote.gov/results](https://ocvote.gov/results) | HTML/TXT | verified |
| Orange, NY | 21 | [Orange County BOE](https://www.orangecountygov.com/169/Board-of-Elections) | HTML/PDF | blocked to scripts |
| Onondaga, NY | 21 | [ongov.net/elections](https://www.ongov.net/elections/) | HTML "Results Caster" | didn't load from scripts |
| Westchester, NY | 20 | [citizenparticipation.westchestergov.com](https://citizenparticipation.westchestergov.com/) | HTML | verified |
| Monroe, NY | 17 | [monroecounty.gov/elections-results](https://www.monroecounty.gov/elections-results) | HTML | verified |
| San Diego, CA | 16 | [sdvote.com](https://www.sdvote.com/) | HTML/PDF | verified |
| Alameda, CA | 15 | [acvote.alamedacountyca.gov](https://acvote.alamedacountyca.gov/) | HTML + RCV rounds | verified |
| Broome, NY | 14 | [broomevotes.com/results](https://www.broomevotes.com/results) | PDF/XLS | unverified |
| San Francisco, CA | 13 | [sfelections.org/results](https://sfelections.org/results/) | HTML/PDF/ZIP + RCV | verified |
| Chautauqua, NY | 13 | votechautauqua.com / county BOE page | HTML/PDF | unverified |
| Multnomah, OR | 14 | [Multnomah County Elections](https://multco.us/departments/multnomah-county-elections-division) | Numbered PDF update reports | verified |
| Santa Clara, CA | 12 | [Clarity – Santa Clara](https://results.enr.clarityelections.com/CA/Santa_Clara/) | Clarity | verified |
| San Mateo, CA | 12 | [smcacre.gov/elections](https://www.smcacre.gov/elections) | HTML/PDF | verified |
| Erie, NY | 12 | [elections.erie.gov](https://elections.erie.gov/) | HTML | verified |
| Niagara, NY | 11 | `ny.votereporting.com/NIA/…` | HTML (vendor portal) | unverified |
| San Bernardino, CA | 10 | [elections.sbcounty.gov/results](https://elections.sbcounty.gov/results/) | HTML | verified |
| Riverside, CA | 11 | [voteinfo.net](https://www.voteinfo.net/) | HTML | blocked to scripts |
| Contra Costa, CA | 9 | [Clarity – Contra Costa](https://results.enr.clarityelections.com/CA/Contra_Costa/) | Clarity | verified |
| Oneida, NY | 8 | [oneidacountynyvotes.gov](https://oneidacountynyvotes.gov/) | PDF (used Enhanced Voting in 2023) | unverified |
| Washington, OR | 8 | [washingtoncountyor.gov/elections](https://www.washingtoncountyor.gov/elections) | HTML/PDF | verified |
| Sonoma, Ventura, Marin (CA) | 14 | Clarity county sites | Clarity | verified |
| Travis, Dallas, Tarrant, Bexar, Denton (TX) | 8 | Clarity county sites | Clarity | verified (Denton already shows Nov 3) |
| Hamilton (OH) | 5 | [Clarity – Hamilton](https://results.enr.clarityelections.com/OH/Hamilton/) | Clarity | verified, Nov 3 listed |
| Hudson, Middlesex, Essex (NJ) | 6 | Clarity county sites | Clarity | verified |

The other ~35 counties each hold 1–7 rows; every one is in the CSV with a verified URL. Notable ones:
[Schenectady](https://www.schenectadycountyny.gov/elections) (live link ~9:30pm),
[Putnam](https://boe.putnamcountyny.gov/), [Nassau](https://www.nassaucountyny.gov/571/Election-Results),
[Cattaraugus](https://www.cattco.gov/election), [Chemung](https://www.chemungcountyny.gov/476/Election-Results),
[Deschutes Elections Central](https://webapps.deschutes.org/Elections/Home/Results/100),
[Polk OR, Nov 3 page](https://www.polkcountyor.gov/1168/November-3-2026-General-Election),
[Franklin OH](https://vote.franklincountyohio.gov/) (Columbus Issue 8), and
[Bay MI](https://www.baycountymi.gov/departments/clerk/elections/election_results.php).

**Lead:** Niagara County publishes on `ny.votereporting.com`, a vendor portal that likely hosts other NY counties too.
It doesn't allow browsing, so each county's own site has to link to its exact page. Check on election night;
it could replace several PDF scrapers.

## Third-party alternatives

| Source | What it covers | Cost | Use it for |
|---|---|---|---|
| **AP Elections API** | Federal, statewide, legislative, statewide measures in all states, plus selected local races; race calls | Paid license (AP also runs a free results program for nonprofit newsrooms) | MA, MI, WI, ME, KY; backstop for any state feed that breaks; race calls |
| **Decision Desk HQ API** | Claims full-ballot coverage down to school boards; contested races only | Paid | The closest thing to one feed for the ~500 local rows; worth a quote |
| **Clarity ENR** (vendor, free to read) | Whichever states/counties use it (see above) | Free | Already counted as official sources |
| **OpenElections** | Precinct-level certified results, volunteer-converted, weeks to months later | Free | Historical/certified backfill only |
| **Ballotpedia** | Candidate and race metadata, winners after the fact | Free to browse | Cross-checking winners; not a live feed |

**Recommendation:** If budget allows, license AP or DDHQ for federal, statewide and legislative races in all 32 jurisdictions
(548 candidate rows plus statewide measures). Use official feeds to verify and to fill the ~580 local and judicial
rows the vendors don't fully cover. Without a
license, the official sources above cover everything except MA, MI, WI and ME on election night. Those four can
show "results pending" until their states post.

## Timing and certification

- **Slow counters:** California (~30 days), Oregon and Washington (mail ballots; daily updates for ~2 weeks),
  New York (canvass up to 25 days), Maine (RCV tabulation days later).
- **Ranked-choice:** Maine U.S. Senate; DC (new in 2026); Oakland, Berkeley and San Francisco local offices.
  Election-night totals are first-round only.
- **Certification** varies, roughly 1–4 weeks by state. The dashboard should show "unofficial" until then.

## Data issues found while mapping

- **Board of Equalization** (CA, 2 rows) was classified as Local Office; the scraper now classifies it as
  State Executive.
- **Vague CA offices** (6 rows) didn't name a county. Five were identified by candidate and are now rewritten by
  the scraper's `OFFICE_OVERRIDES`. They are Fresno County Superior Court Seat 7 (Salazar), Riverside County
  Superior Court Seat 10 (Garcia), Los Angeles County Superior Court Offices 131 and 65 (Ross, Clayton), and Tulare
  Local Healthcare District Area 3 (Price). Kristina Pine's "Board of Education" stays as listed until her race is
  confirmed (see below).
- **"Your 2 Cents" (OR)** is a City of Portland participatory-budgeting measure (Multnomah County).
- **MA Questions 8 and 9 are real statewide questions.** Massachusetts has 9 this year: Q8 would ban retail
  marijuana sales, and Q9 is a veto referendum on the 2024 gun law.
- **Columbus Issue 8** is confirmed on the ballot; the council's competing Issue 9 overrides it on conflicts if both pass.

### Still unresolved (5 rows)

| Row | Question | How to settle |
|---|---|---|
| Ellen McHale, "Charlestown Town Council" (NY) | No NY town by that name, and no trace of the candidate | Ask WFP; possibly Charlton (Saratoga County) |
| Kristina Pine, "Board of Education" (CA) | Resigned her Simi Valley USD seat in 2025; which board now? | Ventura County candidate list |
| Kaitlin Parker, Malone Village Trustee (NY) | Malone votes in November, but her 2026 candidacy isn't confirmed | Franklin County BOE candidate list |
| Morgen Fleisig, Hastings-on-Hudson Trustee (NY) | No 2026 trustee candidacy found (lost 2025 mayoral primary) | Westchester BOE candidate list |
| Oregon "Initiative Petition 9-2026-I-01" | Identifier not found anywhere; "9-" suggests Deschutes County | Deschutes County voters' pamphlet |

## Before election night

1. Decide on an AP/DDHQ license; it changes how much official scraping is needed.
2. Settle the 5 unresolved rows above.
3. Capture election IDs as they post: Colorado Clarity EID, Georgia `publicElectionId`, Texas election ID,
   DC election entry, Maryland `general_results/` page.
4. Plan for bot protection (AZ, OH, DC, KY, TN, Riverside, several NY counties): a headless browser or a browser-like
   client with modest polling (every 2–5 minutes).
5. Map each WFP row to the exact contest name/ID in its feed. Feeds use different naming, e.g. NC lists
   "DISTRICT ATTORNEY DISTRICT 16" rather than "Durham County District Attorney".

## `results_sources.csv` columns

| Column | Meaning |
|---|---|
| `id`, `name`, `office`, `office_category`, `state` | From `candidates.json` |
| `results_level` | `state`; `local (via state source)`; `county (via state Clarity)`; `county`; `county (unconfirmed)` |
| `county` | County (or district) whose office reports the race, when not statewide |
| `source_name`, `source_url` | Human-facing results page (`TBD` = still to find) |
| `data_endpoint` | Machine-readable endpoint pattern, when one was found |
| `platform`, `format` | Vendor/system and data format |
| `live_on_election_night` | `yes`, `partial` (slow or batch), `no` |
| `url_status` | `verified` (loaded), `blocked` (exists, bot-protected), `unverified` (found, not loaded), `missing` |
| `nov3_ballot` | `expected` (not individually checked), `confirmed`, `no` (decided earlier in 2026), `unconfirmed` |
| `nov3_note` | Evidence for `nov3_ballot`, including date and outcome for races already decided |
| `source_notes` | Platform-specific notes |
| `flags` | Notes on the row: misclassification, how a vague office was identified, multi-county sums, RCV, AP recommended |
