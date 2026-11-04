# Election-night scraper notes

What each results run on Nov 3, 2026 found, and what was fixed along the way. Newest runs last. Times are Eastern;
each run's full log is in `logs/results/<run id>.log` (run ids are UTC).

"Races with votes" counts WFP endorsements whose matched contest has any votes (`counting` in
`data/results/wfp_results.json`). "Leading" means WFP's choice is in a winning position right now; nothing here calls
a race.

See also [election-results-scraper-plan.md](election-results-scraper-plan.md) (design and build status) and
[candidate-changes.md](candidate-changes.md) (changes to WFP's candidate list).

---

## Summary

| Time (ET) | Races with votes | WFP leading | New sources reporting |
|---|---:|---:|---|
| 6:05pm | 0 | – | none (no polls closed) |
| 7:10pm | 19 | – | Georgia |
| 7:47pm | 36 | 33 | Ohio |
| 8:21pm | 94 | – | Pennsylvania, Rhode Island, North Carolina, Hamilton County OH, Denton County TX |
| 8:25pm | 114 | 109 | Connecticut |
| 8:39pm | 131 | 123 | Delaware |
| 9:15pm | 245 | 228 | NYC (new scraper), Colorado, New Mexico |
| 9:23pm | 259 | 238 | Erie County NY (new scraper) |
| 10:26pm | 363 | 313 | Westchester County NY (new scraper), Maryland (Montgomery County) |

Not yet posted by 10:26pm: Florida, South Carolina, Bexar/Dallas/Tarrant counties (TX), Hudson and Middlesex
counties (NJ), and the five California Clarity counties. California, Oregon and Washington close at 11pm ET.

---

## Before polls closed

### 6:05pm: first run of the night

- Candidate scraper: one swap since the morning. Adam Hamawy (NJ-12) was added and Ras Baraka (Mayor of Newark,
  decided in May) was removed. Hamawy took id 482, so no other ids shifted. See candidate-changes.md.
- All 33 sources ran without errors. No votes anywhere.
- Feeds that changed since the last run: PA, GA, UT, NM, CO, CT (setup changes, not votes).
- Not yet posting a Nov 3 election: SC, FL, four Texas counties, Hudson and Middlesex (NJ), five California counties.
- Matching: 521 auto, 16 needs review, 52 unmatched, 619 no source (up from 410 auto as more feeds posted their
  ballots).

---

## Georgia and Ohio

### 7:10pm: first results (Georgia)

- 19 Georgia races had votes. Nothing else had reported.
- **Problem: Georgia's "% reporting" was misleading.** Single-county State House districts read "100% reporting" ten
  minutes after polls closed. Georgia's statewide file counts *counties* that have posted anything, including early
  votes, not precincts. Statewide races read 8.2% because 13 of 159 counties had posted.
- **Fix:** Enhanced Voting state files now report "13 of 159 counties posted results" instead of a percentage
  (Rhode Island: "cities and towns"). County files, which count precincts, keep the percentage. A new
  `Reporting.as_percent` flag keeps the percentage off after results are stored and reloaded.
- DeKalb County's races read "0.0% reporting" next to early votes. That's accurate: its county file counts precincts
  that have fully reported.

### 7:25pm: source links

- Each expanded result on the dashboard now links to where it came from ("Source: Georgia Secretary of State ↗").
  Clarity races link to that election's own page; hand-entered races use their row's `source_url`.
- All 32 source pages loaded; every matched race had a link.

### 7:47pm: 36 races

- Georgia 25, Ohio 11. WFP leading in 33.
- Ohio's first numbers are early and absentee votes, so they show "0.0% reporting" (no precincts in yet).
- North Carolina's feed hadn't changed since before its 7:30 close.
- Trailing: Amanda Hollowell (GA-1, 49%), Suzanna Karatassos (GA HD-120, 34%), Ethan Wolfe (GA HD-151, 18%,
  three-way).

---

## The 8pm wave

### 8:21pm: Pennsylvania, Rhode Island, North Carolina and Ohio counties

- 94 races with votes. New: PA 18, RI 12, NC 8, Hamilton County 5, Denton County 1. Travis County (TX) posted its
  ballot.
- **Problem: a wrong Texas match.** Dr. Jared Williams (Tarrant County Commissioner) matched a Travis County utility
  district race on name alone. Clarity county contests were labeled "Travis", not "Travis County", and the county
  filter keys on the word "County", so other counties' races got through for every Clarity county source.
- **Fix:** Clarity county contests are labeled "<name> County". Williams correctly shows as not tracked until
  Tarrant County posts.
- **Problem: Pennsylvania's reporting figure is statewide only.** Every district race showed "0.36%" and the feed's
  raw message ("33 Out of 9,066 Districts (0.36%) - IN PERSON BALLOT REPORTING ONLY").
- **Fix:** PA district races show "Statewide, 33 of 9,066 districts reported (in-person ballots only)". Statewide
  races keep the percentage.
- Two Rhode Island matches went to review for nicknames (Jackie/Jacqueline Goldman, Libby/Elizabeth Merrill); both
  are correct.

### 8:25pm: Connecticut

- 114 races with votes, WFP leading 109.
- **Problem:** Connecticut also reports precincts statewide only. Jahana Hayes's CT-5 race showed "1 of 776".
- **Fix:** CT district races show "Statewide, 1 of 776 precincts reported".
- Trailing: Karatassos and Wolfe (GA), Caleb Price (OH HD-30, 47%), Katie Koehler Wagner (OH HD-80, 41%), and the
  Winton Woods school levy (Hamilton County, 45% Yes).

### 8:39pm: Delaware, and Nelly Burdette

- 131 races with votes, WFP leading 123.
- **Nelly Burdette (RI SD-17) fell behind** once all three towns posted: Paolino 1,778 (42.5%), Burdette 1,683
  (40.2%), Petrarca 526, Barr 194. She had led 240 to 208 with two of three towns in.
- Delaware posted 13 races; WFP led all of them.
- Also turned to trailing: Veronicka Vega (RI HD-4, 49.1%), Laalitya Acharya (OH HD-56, 49.8%).
- **Clarity returned HTTP 502** for Colorado, Denton, Travis and Hamilton. The scraper kept their previous results.

---

## New York

### 8:50–9:00pm: building the New York scrapers

New York has 390 WFP endorsements, more than any state, and had no results source. Its sites only show their results
format once results start, so the scrapers were built against the live sites just before the 9pm close.

- **NYC (`enr.boenyc.gov`)**, new parser in `counties/ny.py`. One "Expand List" page per office lists every district
  with each candidate's party lines (Democratic, Working Families) and "Percentage of Scanners Reported". A "*" after
  a title marks the city's share of a race that crosses the city line (statewide offices, NY-3, NY-16, SD-34,
  SD-36); those are partial. 55 WFP races matched.
- **NYS Board of Elections (`nyenr.elections.ny.gov`)** still returns 403 to scripts. WFP's state legislative races
  outside NYC have no source.
- **Westchester** is on Enhanced Voting (`app.enhancedvoting.com/results/public/westchester-county-ny`), so it's
  configuration. 19 races matched; 9 confirmed by hand (county legislators, plus Cat Sayles and Len Simon).
- **Erie** uses Results Caster, a JSON API found through the browser's network requests:
  `api/resultscasts/<slug>/shell` and `.../results/<Election Day | Early Voting | Absentee>`. New module
  `platforms/resultscaster.py`. Erie's Nov 3 election is titled "General Election 2026 test" (slug `testgen`) but
  holds the real ballot. 12 races matched, including a manual match for Rathi Ravi (WFP lists "Bharathy (Rathi) S
  Ravichandran (Ravi)").

Fixes made while building:

- **County sources matched other districts.** NYC's contests sent four upstate candidates to review on surname alone
  (Patrick Carroll AD-96 vs Robert Carroll AD-44, and others), and review matches get published. A county-level
  source now never matches "any district" or the whole-state fallback.
- **"Member of Assembly"** (Westchester, Erie) wasn't recognized as a State Assembly race. Westchester's Assembly
  contests were treated as local and complete.
- **Enhanced Voting split fusion candidates** into one choice per party line. Lines are now combined, with per-line
  votes in `party_lines`, and county Enhanced Voting sources mark state and federal contests partial.
- **"Legislature" and "Legislator"** now count as the same office word, so Erie's and Westchester's county
  legislators match automatically.
- **Status filter default:** the dashboard now opens on Leading and Trailing races only.

### 9:15pm: NYC results

- 245 races with votes, WFP leading 228.
- **NYC's scraper worked on real counts:** 50 races at 15–45% of scanners reported, WFP leading all of them. Valdez
  (NY-7) 85%, Lander (NY-10) 85%, Avila Chevalier (NY-13) 89%, Ocasio-Cortez (NY-14) 79%. Closest: Janice Purvis
  (Civil Court District 6) 52%, Chris McCreight (AD-46) 57%.
- Colorado posted 34 races (its sources took almost 2 minutes) and New Mexico 15.
- Westchester and Erie answered but had no votes yet.
- Trailing (17), including Lamont/Bysiewicz (CT Governor, 49.2%), Annette Blackwell (OH Auditor, 49.7%), Vanessa
  Enoch (OH-8, 49.5%), Cara Jacob (OH SD-7, 48.3%), Vic Meyers (CO HD-47, 28.5%), Mallory Martin (CO HD-54, 32%),
  Caleb McCoy (PA, 45.5%).
- Clarity errors again (HTTP 502/504) for Denton, Travis and Hamilton.

### 9:23pm: Erie results

- 259 races with votes, WFP leading 238.
- **Erie's scraper worked on real counts:** all 12 races, from early votes ("0 of 652 districts reported"). Steven
  Meyer (County Clerk) 58.6%.
- Turned to trailing: Erick Russell (CT Treasurer, 48%), Mae Flexer (CT SD-29, new, 41%), Ian Schwartz (OH HD-62,
  45.6%), Rob Gurtcheff (PA HD-170, 43%).
- New Mexico returned HTTP 503; Colorado, Denton and Travis got Clarity errors. Previous results kept.

---

## Later evening

### 10:24pm and 10:26pm: Westchester, Maryland, and two display fixes

- 363 races with votes, WFP leading 313. New: Colorado (84 total), Connecticut 33, Westchester 19, New Mexico 22,
  Maryland 9 (Montgomery County; Will Jawando 79% for County Executive).
- **Problem: New Mexico showed shares of about 0.5%.** Its feed's `CandidatePercentage` is a fraction (0.4513 for
  45.1%). **Fix:** shares for New Mexico and Nebraska are computed from the votes.
- **Problem: Westchester showed "100% reporting" at 10:24.** Its `reportingUnits` counts a precinct once any of its
  ballots are in; the breakdown showed 0 of 49 fully reported and 49 partly. **Fix:** when Enhanced Voting gives the
  breakdown, only fully reported precincts count ("0 of 49 precincts fully reported, 49 partly").
- Clarity answered this run, so Colorado and Texas are current.
- Now ahead in Connecticut: Lamont/Bysiewicz 57%, Russell 58%, Flexer 50.2%.
- Now behind: Hollowell (GA-1, 49.6%), Jackie Baker (PA SD-20, 40%), Rathi Ravi, Sara Marmion and Zachary Beaudoin
  (Erie Legislature 6, 8, 11), Laura Parra (NM HD-32, 45%), Leslye Oquendo-Thomas (Westchester Legislature 17, 29%).
- Colorado ballot measures: WFP's side trails on Amendment 85 (49.8%) and Propositions 132–137 (39–50%).
- Boulder City Council elects 5 of 13; WFP's Jamillah Richmond and Rachel Rose Isaacson are 7th and 8th.

---

## Feed quirks worth remembering

| Source | Quirk | How it's handled |
|---|---|---|
| Enhanced Voting state files (GA, UT, WA, RI) | "Reporting units" are counties (RI: cities and towns) that posted anything | Shown as a count, not a percentage |
| Enhanced Voting county files (Westchester) | A precinct counts as reporting once any ballots are in | Only "Fully Reported" precincts count when the breakdown is given |
| Enhanced Voting (NY) | One ballot option per party line | Combined into one choice with `party_lines` |
| Pennsylvania, Connecticut | Precincts reporting is statewide only | District races show it as labeled statewide text |
| NM/NE results CSV | `CandidatePercentage` is a fraction | Percentages computed from votes |
| Clarity counties | Jurisdiction was the bare county name | Labeled "<name> County" so the county filter applies |
| Clarity (all) | HTTP 502/504 under election-night load | Previous results kept; retried next run |
| NYC ENR | "*" marks the city's share of cross-city races | Marked partial |
| Erie Results Caster | Nov 3 election slug is `testgen`, titled "test" | Found by date; non-test titles preferred if one appears |
| NYS BOE | 403 to scripts | No source; state legislative races outside NYC stay `no_source` |

## Still open

- Florida, South Carolina, three Texas counties, two New Jersey counties and five California Clarity counties
  hadn't posted a Nov 3 election by 10:26pm.
- Dutchess and Ulster (66 NY races) post PDFs; not built.
- Onondaga (21 NY races) uses Results Caster and may work with `platforms/resultscaster.py` if its site is
  reachable.
- Races that cross county lines (for example Nathalia Fernandez, SD-34) only have partial shares and stay off the
  dashboard until partials can be summed.
