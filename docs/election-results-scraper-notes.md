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
| 10:59pm–11:05pm | 373 | 322 | Florida (new scraper), Dane and Kenosha counties WI (new scrapers), Milwaukee WI (6 by hand) |
| 11:10pm | 499 | 410 | Oregon, California (state and Orange County), Utah's legislative races, Washington |
| 11:21pm–11:25pm | 504 | 415 | Wayne and Washtenaw counties MI (new scrapers) |
| 12:16am | 576 | 480 | Washington (King County), more California, Connecticut and New Mexico |
| 12:25am | 601 | 497 | Santa Clara, Contra Costa, Sonoma, Ventura (CA) and Hudson (NJ), via known Clarity ids |
| 12:48am | 606 | 500 | South Carolina (new scraper, XLSX snapshots) |
| 1:43am | 623 | 519 | Connecticut (15 more), Wegela (MI HD-26) |
| 2:16am | 625 | 523 | Connecticut (2 more) |
| 3:35am | 628 | 524 | Connecticut (3 more) |
| 9:46am | 628 | 523 | (none new; morning updates) |
| 10:00am | 825 | 663 | 15 NY counties on Enhanced Voting, Chautauqua NY, San Diego, San Mateo, San Bernardino (new sources) |
| 10:08am | 854 | 689 | Arizona and DC (new sources) |
| 10:17am | 870 | 703 | Massachusetts (entered by hand from AP) |
| 10:31am | 915 | 742 | NY districts summed from county results; NYC leader fix |
| 10:44am | 958 | 777 | Onondaga, Nassau, Albany, Schenectady, Saratoga and 6 more NY counties (new sources) |
| 10:52am | 972 | 782 | Niagara NY (new source) |
| 10:51pm | 973 | 783 | Connecticut (2 more); 5 sources now 403, 3 timed out |
| 11:07pm | 985 | 794 | Michigan statewide and legislative races (entered by hand) |
| 11:18pm | 1,019 | 816 | Los Angeles County's counts (bug fix), Multnomah ranked-choice (new source) |
| Nov 5, 9:55am | 1,019 | 816 | (none new; 12 counts changed) |
| Nov 7, 10:29am | 1,019 | 819 | (none new; 531 counts changed, California counties updated) |
| Nov 8, 7:05pm | 1,019 | 821 | (none new; 215 counts changed) |
| Nov 9, 2:04pm | 1,019 | 822 | (none new; 159 counts changed) |

Still missing at 2:04pm Nov 9: Bexar/Dallas/Tarrant counties (TX), Middlesex (NJ) and Marin (CA). See "12:25am: the silent Clarity counties" below.

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

### 10:59pm: Florida

- The Clarity copy of Florida's results never listed Nov 3, and the state's archive site
  (`results.elections.myflorida.com`) only lists past elections. Election-night results are on
  **floridaelectionwatch.gov**, whose Downloads page links a tab-delimited file of every state-run contest by county.
- New source `states/fl.py` replaces the Clarity entry. **The plain file URL serves a stale cached copy** (Nov 2's
  zeros); the link on the Downloads page carries a `?v=` number that returns the current file, so the scraper reads
  the link each run.
- Totals match the site exactly. **Angie Nixon (U.S. Senate) trails:** Moody 4,194,216 (50.9%), Nixon 3,949,306
  (47.9%), Gillespie 94,055 (1.1%), with 5,551 of 5,626 precincts in.
- **Bug found on the way:** `names.yes_no` read Florida's "No for Rejection" as Yes, because "for" matched first. A
  leading yes or no now decides.

### 11:03pm: Wisconsin counties

- Wisconsin doesn't compile election-night results, and we have no AP license, so the route is county sites. WFP's
  26 legislative races are mostly in Milwaukee, Racine/Kenosha, Madison, Green Bay and Eau Claire.
- **Dane County** has a public API (`api.danecounty.gov/api/v1/elections`): one call returns every race with
  precincts reported. **Kenosha County** has a results page (`apps.kenoshacounty.org/ElectionResults_v4/?eid=70`).
  New sources in `counties/wi.py`.
- **Milwaukee County's** election-night page (512 of 521 wards at 9:43pm) returns 403 to scripts; not scraped.
  Racine and Brown post PDFs.
- Only districts wholly inside one county count as complete: AD-76 (Dane), AD-64 and AD-65 (Kenosha). The three
  statewide questions, SD-17 and AD-51 are partial from Dane alone.
- Results: Dina Nina Martinez-Rutherford (AD-76) 91.8% at 89% of precincts; Tip McGuire (AD-64) 58.5%; Ben DeSmidt
  (AD-65) 56.8%. Kenosha's page gives no precincts-reporting count.

### 11:05pm: Milwaukee County by hand

- Six Milwaukee races entered in `data/results/manual_entries.csv` from the county's election-night page (last
  updated 9:43pm CT): AD-8 Ismael Luna 85.1%, AD-11 Sequanna Taylor 90.5%, AD-14 Angelito Tenorio 59.8%, AD-18
  Margaret Arney 86.1%, AD-19 Ryan Clancy 85.8%, AD-20 Christine Sinicki 67.4%. All lead.
- Only districts shown to lie entirely in Milwaukee County were entered. Left out:
  - **AD-13 (Zimmerman) and SD-5 (Vining):** Waukesha County's results list both. SD-5's 49 Milwaukee wards are
    exactly AD-13 plus AD-14; its third district, AD-15, is in Waukesha.
  - **SD-21 (Jung):** Milwaukee lists AD-61 and AD-63, so it's split with Racine County.
  - **AD-21 (Bukiewicz) and SD-7 (Larson):** AD-21 borders Racine County, whose site returns 403 to scripts, so it
    couldn't be confirmed. SD-7 is AD-19 + 20 + 21 (its 88 wards match), so it depends on AD-21.
- No reporting percentage was entered. Milwaukee's "wards reporting" excludes absentee ballots counted centrally
  (the City of Milwaukee counts that way), so "100%" would overstate it. The ward counts are in each row's note.
- These numbers only change when someone re-enters them. After editing the file, run
  `scrape_results.py run --sources manual` (plain `match` reuses the last stored pull).

### 11:10pm: the West Coast

- 499 races with votes (up from 373 after the Florida and Wisconsin additions), WFP leading 410. All sources ran
  without errors; Clarity answered.
- **New: Oregon 68, Orange County 20, California 19, Connecticut 11 more, Utah 6, New Mexico 1, Washington 1.**
- Oregon: Kotek (Governor) 54%, Merkley (U.S. Senate) 59%, Bonamici (OR-1) 74%, Hoyle (OR-4) 55%. Oregon votes by
  mail, so its "0.0% reporting" is the feed's precinct count, not a sign of no votes.
- California's first counts are early mail ballots (5.6% of precincts statewide). Jane Kim (Insurance Commissioner)
  54%, Randy Villegas (CA-2) 60%. WFP's side trails on Props 4, 5, 40, 41, 42, 43 and 45, and leads on 1, 2, 3, 38,
  39 and 44.
- Utah's four single-county House districts (Salt Lake and Utah counties) posted: Otterstrom, Hayes, Dominguez and
  Chappell all lead.
- Trailing for the first time (selected): Sean Frame (CA SD-6, 49%), Leila Namvar (CA AD-47, 44%), Roy Kaufmann (OR
  HD-18, 35%), Sierrah Williams (OR SD-6, 46%), Angeline Nicole Basett (OR SD-26, 49%), Brandi Mandato (CT SD-34,
  47%), and several Orange County and Oregon city council races.
- Flipped to trailing: Jonathan Bradner (OH HD-29, 50.0%), Jon Lloyd (PA HD-40, 48.5%), Brad Chambers (PA HD-41,
  49.9%).
- Flipped to leading: Bob Fernandez (CT HD-48, 51.7%), Suzanne Lovig (CT HD-66, 50.3%), and WFP's side on Colorado
  Proposition 137 (50.0%).
- Milwaukee's hand entries weren't re-read this run; they're as of 9:43pm CT.

### 11:21pm: Wayne County, Michigan

- Michigan's Secretary of State posts statewide results about a day later, so election night means counties.
  **waynecountymi.gov returns 403 to scripts** (pages and PDFs), but its results page links to **TotalVote**
  (`michigan.totalvote.com/Wayne`), which doesn't. One server-rendered page per category (`ResultsSW.aspx?type=CON`,
  `SEN`, `REP`). New source `counties/mi.py`. No other Michigan county is on TotalVote.
- Wayne was slow: 7 of 770 precincts at 11:06pm. The votes so far are mostly absentee counting boards.
- Which districts lie entirely in Wayne County came from Wikipedia's district lists (Michigan's own results archive
  wasn't reachable): **MI-13, SD-2, HD-26 and HD-27** are Wayne only. MI-13 also takes in a sliver of Grosse Pointe
  Shores in Macomb County (a handful of votes), so it's treated as complete. **MI-12 (Tlaib)** includes Southfield
  (Oakland), **HD-7 and HD-8** include Oakland, and **HD-11** includes Macomb, so those are partial.
- Results: Donavan McKinney (MI-13) 75%, Abbas Alawieh (SD-2) 90%, Jaime Churches (HD-27) 63%. Dylan Wegela (HD-26)
  has no votes yet.
- **Bug caught on the first run:** the contest-title pattern matched lazily from the first `<h1>` on the page, so
  each title swallowed the previous contest's candidates. The title can no longer cross tags, and a test covers it.
- Partial for now, from Wayne alone: Tlaib 93% of Wayne's share (MI-12), Tonya Myers Phillips 95% (HD-7).

### 11:25pm: Washtenaw and Bay counties, Michigan

- **Washtenaw** posts election-night results at `electionresults.ewashtenaw.org/electionreporting/nov2026/index.jsp`
  (linked from washtenaw.org/election-results; the old Elections Division URL now redirects elsewhere). Every race is
  in one summary table with early, absentee, election-day and total votes. New source `mi.washtenaw` in
  `counties/mi.py`.
  - Yousef Rabhi (Ann Arbor mayor) 97% (effectively unopposed), Ryan Bartholomew (Ann Arbor Ward 3) 92%.
  - Precincts counted is only countywide (36 of 112 fully counted at 10:46pm), so it's shown as labeled text.
  - HD-23 (Jason Morgan) also has 4 Wayne precincts, so it's partial. Washtenaw's share: Morgan 78%.
- **Bay County** posts PDFs (`November 3, 2026 Unofficial Summary Results`). Read by hand: **the Bay City
  Commission races (Kenzie Colton, Ward 3; Chris Runberg, Ward 7) aren't on the county's report.** The city may
  report them itself, or they may not be on this ballot. Worth checking with Bay City or WFP.
- Bay's report also shows its share of the statewide races: El-Sayed 47% to Rogers 51%, Gilchrist 50.1%, Savit 48%
  (Bay County only, not on the dashboard).

### 12:16am: King County and more California

- 576 races with votes, WFP leading 480. All sources ran without errors.
- **New: California 24, Connecticut 16, Washington 16, New Mexico 15, Oregon 1.**
- Washington: Pramila Jayapal (WA-7) 88%, Teresa Mosqueda (King County Council) 70%, Shaun Scott (LD-43) 97%. Hannah
  Sabio-Howell (LD-43 Senate) trails at 23%, and Danny Tarkenton (Prosecuting Attorney) at 47%.
- California House: Lateefah Simon (CA-12) 81%, Ro Khanna (CA-17) 72%, Aisha Wahab (CA-14) 59%; Connie Chan trails
  Scott Wiener in CA-11 (43%), and Mai Vang trails Doris Matsui in CA-7 (41%). Jane Kim (Insurance Commissioner) is at
  51.5% with 49% of precincts in.
- California props: WFP's side now leads on 5, 41, 43 and 45 (it trailed on all four at 11:10pm). It still trails
  on 4, 40 and 42.
- Flipped to leading: Sean Frame (CA SD-6, 50.7%), Leila Namvar (CA AD-47, 57%), Ethan Werstler (CT SD-35, 54%),
  Elouise Brown (NM San Juan County Commission), and Nelly Burdette (RI SD-17, 43.4% in a four-way race; 4,819 to
  Paolino's 4,318).
- Flipped to trailing: Irene Bonham (Douglas County CO Commission, 49.6%), Suzanne Lovig (CT HD-66, 47%), David
  Mooney (NM HD-38, 49.7%), Joanna Robinson (OR HD-15, 48.5%).
- Amanda Hollowell (GA-1) trails at 49.3% with all 15 counties posted. Angie Nixon (FL U.S. Senate) is at 48.0% with
  5,574 of 5,626 precincts.
- Wayne County still shows under 1% of precincts in. Milwaukee's hand entries (as of 9:43pm CT) weren't re-read.

### 12:25am: the silent Clarity counties

- Eleven Clarity sources had reported "no Nov 3 election listed" all night. **Most hadn't moved: they linked
  tonight's election from their own sites but never added it to Clarity's election list.** Clarity's own list page
  says "Elections not available!", and `elections.json` is `[]`, but `<site>/<eid>/current_ver.txt` works.
- **Fix:** a Clarity source can carry a known election id (`eid=`) to use when the list is empty. Ids, each read
  from the county's results page and checked against the election's settings date:
  Santa Clara 127570, Contra Costa 127405, Sonoma 127275, Ventura 127362, Hudson (NJ) 127495.
- 34 races came in: Santa Clara 13, Contra Costa 8, Sonoma 7, Ventura 6, Hudson 4. Three Sonoma/Contra Costa
  matches were confirmed by hand (Becca/Rebecca Barrett; Paun and Bagby, where "County Supervisor, 2nd District"
  didn't overlap "Board of Supervisors" by word).
- Selected: Claudia Jiménez (Richmond mayor), the four Hudson commissioners and Melanie Jones-Carter (Santa Rosa)
  lead. Trailing include Kevin Park (Santa Clara mayor, 4th of 6), Tamisha Torres-Walker (Antioch D1, 44%), Gordon
  Chester (San Jose D9, 46%) and Caitlin Quinn (Sonoma Board of Education, 48%).
- Two Santa Clara candidates (Anthony Montes, East Side Union HSD; Alexander Gvatua, Foothill-De Anza) aren't on the
  county's ballot. Their trustee areas aren't contested, so they stay unmatched.
- **Still missing:**
  - **South Carolina** left Clarity: scvotes.gov posts timestamped XLSX files
    (`/wp-content/uploads/2026/11/2026-11-03-1130PM-General-Election-Results.xlsx`). Needs a small XLSX parser.
  - **Marin's** results page still links an August election (127071). **Middlesex's** results page is a 404.
  - **Bexar, Dallas, Tarrant:** their elections.json lists only older elections; the Nov 3 sites weren't found tonight.

### 12:48am: South Carolina

- The SC Election Commission didn't use Clarity this year. `scvotes.gov/2026-general-election-results/` links a new
  XLSX snapshot every 15–30 minutes (`/wp-content/uploads/2026/11/2026-11-03-1130PM-General-Election-Results.xlsx`),
  oldest first. New source `states/sc.py` replaces the Clarity entry: it takes the last link and reads the workbook
  with the standard library (no new dependency).
- Each contest is a sheet: the title (with double spaces) in row 1, candidate names above blocks of seven vote-type
  columns (the last is "Total Votes"), one row per county, then "Total:". No precincts-reporting count.
- The "12AM" file is dated 11-03 but means midnight going into Nov 4; `snapshot_time` handles that.
- All five WFP races matched (midnight snapshot):
  - Courtney McClain (SC-4) trails William Timmons, 129,561 to 146,808 (45.7%).
  - Jumelle Brooks (HD-12) 54.9%, Keishan Scott (HD-50) 62.2% and Sonja Ogletree Satani (HD-98) 53.7% lead.
  - Julie Zimmerman (HD-71) trails, 41.6%.

### 1:43am: late counts

- 623 races with votes, WFP leading 519. All sources ran without errors; the five sources above still list no
  Nov 3 election.
- New: Connecticut 15 more House and Senate races (including Gary Winfield, SD-10, and Rick Lopes, SD-6, 53%),
  Ash Kalra (CA AD-25, 73%), and Dylan Wegela (MI HD-26, 72%).
- Wayne County is still slow (7% of precincts in for MI-13): McKinney 80%, Alawieh 79%, and Jaime Churches (HD-27)
  down to 50.1% at 35% of precincts.
- Flipped to leading: Kim Becker (CT HD-62, 50.1%), Brandi Mandato (CT SD-34, 50.0%), Cari Power (Socorro County NM),
  David Mooney (NM HD-38, 52.4%), Kipperlyn Sinclair (Washington County OR, 49.8%, multi-candidate).
- Flipped to trailing: Jennifer Engle (Moulton Niguel Water District, multi-seat).
- Effectively complete and trailing: Angie Nixon (FL U.S. Senate) 48.0% with all 5,626 precincts in; Amanda
  Hollowell (GA-1) 49.3% with all 15 counties posted; Jackie Baker (PA SD-20) 38.5%.
- Still close: Jane Kim (CA Insurance Commissioner) 51.5% at 72% of precincts; Sean Frame (CA SD-6) 50.3% with all
  precincts in (California keeps counting mail ballots for days); Laura Parra (NM HD-32) 46.7% at 29 of 31 precincts.
- South Carolina hadn't posted a snapshot after midnight. Milwaukee's hand entries weren't re-read.

### 2:16am: counts still moving

- 625 races with votes, WFP leading 523. All sources ran without errors; the same five list no Nov 3 election.
- Vote counts changed in 171 races, mostly Colorado (35), Oregon (22), California (21 state, 20 Orange County, 13
  Santa Clara, 8 Contra Costa), New Mexico (31) and Connecticut (12).
- New: Ronald Napoli Jr. (CT HD-73, 71%) and Corey Paris (CT HD-145, unopposed).
- Flipped to leading: Chad Cardillo (CT HD-83, 54.8%), Sara Duncan (Marion County OR, 50.4%), Maria Hinojos Pressey
  (Marion County OR, 50.6%).
- Flipped to trailing: Sean Frame (CA SD-6), now 49.1% with all precincts in. California's later mail-ballot counts
  will decide it.
- Wayne County at 19% of precincts for MI-13: McKinney 72%. Jaime Churches (HD-27) 50.2% at 75%.
- Connecticut at 639 of 775 precincts: Mandato (SD-34) 50.0% and Becker (HD-62) 50.1% are still on the line.

### 3:35am: two near-ties

- 628 races with votes, WFP leading 524. All sources ran without errors; the same five list no Nov 3 election.
- Vote counts changed in 211 races, mostly Oregon (44), Colorado (38), California (31 state, 20 Orange County, 12
  Santa Clara, 8 Contra Costa, 7 Sonoma), New Mexico (28) and Connecticut (13).
- New: Emmanuel "Manny" Sanchez (CT HD-24, 71.5%), David DeFronzo (CT HD-26, 68.8%), Cristin McCarthy Vahey (CT
  HD-133, 67.0%).
- Flipped to trailing: Chris Kluwe (CA AD-72), behind by 60 votes of about 155,000 (77,683 to 77,743) with all
  precincts in; Marie Tsaasan (Aliso Viejo council D3, Orange County), behind by 11 (1,001 to 1,012). Both will move
  as California counts mail ballots.
- Sean Frame (CA SD-6) slipped to 48.2%. Jessie Lopez (CA AD-68) 47.6% with all precincts in.
- Wayne County at 22% of precincts for MI-13: McKinney 72%. Jaime Churches (HD-27) 51.7% at 75%.
- Connecticut at 694 of 775 precincts: Mandato (SD-34) leads by 25 votes, Becker (HD-62) by 34.

### 9:46am: morning updates

- 628 races with votes (no new ones), WFP leading 523. All sources ran without errors; the same five list no Nov 3
  election. Michigan's statewide file isn't posted yet.
- Vote counts changed in 143 races: California (29 state, 20 Orange County, 6 Sonoma, 6 Ventura), Colorado (27),
  Oregon (17), Connecticut (9), Pennsylvania (9), Georgia (6), Utah (5), Ohio (4).
- Flipped to trailing: Naseem Zubi (Pueblo County Assessor, CO), 49.3%, 894 behind at 98.8% of precincts.
- Chris Kluwe (CA AD-72) fell from 60 to 2,605 behind (49.2%). Marie Tsaasan (Aliso Viejo D3) is 10 behind.
- Wayne County now shows all precincts in: McKinney (MI-13) 76.3%, Jaime Churches (HD-27) 51.7%, up 1,641.
- Connecticut at 695 of 775 precincts; Mandato (+25) and Becker (+34) unchanged.
- Close leads in Pennsylvania with mail ballots still out: Meriam Sabih (HD-131) +673, Rachel Cuevas (HD-187) +677,
  Mark Pinsley (SD-16) +3,101.

### 10:00am: tier 1 county sources

- 19 new county sources, 197 more races with votes (825 in all), WFP leading 140 of them (663 in all).
- **New York, 15 counties on Enhanced Voting:** Orange, Monroe, Broome, Oneida, Rockland, Clinton, Suffolk, Putnam,
  Rensselaer, Columbia, Cattaraugus, Chemung, Dutchess, Ulster, Sullivan. Found by trying
  `app.enhancedvoting.com/results/public/api/jurisdictions/<name>-county-ny` for every county with a WFP race.
  Dutchess and Ulster, which I'd expected to need PDF parsing, are on it too.
- **Chautauqua NY:** its results site (`enr.chqvotes.com`) reads one XML file, `Default_3_0.xml`; new parser.
- **San Diego, San Mateo, San Bernardino:** Live Voter Turnout, like Orange County. San Diego's results address
  redirects to the results page itself; San Bernardino's forwards browsers by script, so the source points at the
  Live Voter Turnout page directly.
- Fixes: Monroe, Rockland and Suffolk prefix the Working Families line ("WOR Kevin Berry"), which left two choices
  per candidate; the prefix is stripped so the lines combine. San Diego appends the party ("XAVIER BECERRA (DEM)").
- Confirmed by hand: 20 first-name variants (Stephen/Steven Krasner, Chris/Christopher Drago, Chuck/Charles Kostyk,
  Nate/Nathaniel Salzman and others, each with the same surname and district) and Bernard "Bernie" Rivers (Orange
  County Sheriff).
- Not found in the county's results: Alexandria Smith (Town of Ulster board; Ulster lists only an unexpired-term
  seat) and Melissa First (Chautauqua Legislature District 17; only Travis Heiser is listed).
- Close among the new ones: Steven Krasner (Newburgh supervisor) 50.0%, Kyle Fendrich (Dutchess LD-15) 49.9%, Trish
  Prunty (Dutchess LD-7) 49.6%, Alex Scialdone (Webster supervisor) and Emily Wallace-Kalouch (Chili supervisor) 49.5%.

### 10:08am: tier 2, Arizona and DC

- 854 races with votes, WFP leading 689.
- **Arizona (22 of 23):** results.arizona.vote shows scripts a Cloudflare challenge, but its Nov 3 link goes to
  Enhanced Voting's shared host (`app.enhancedvoting.com/results/public/Arizona/110326GeneralElection`), which
  scripts can read; configuration only. Confirmed by hand: Clara Pratte and Jonathon Hill (Corporation Commission)
  and two WFP misspellings, Sarah Liguori (LD-5) and Priya Sundareshan (LD-18). Ed Hermes (Phoenix council D4) has no
  source: Maricopa's file has no city races, and Phoenix runs its own elections.
- Arizona propositions with WFP's position trailing: 141 (49.3%), 317 (43.0%), 318 (41.1%). Arizona's counties are
  still counting; every county has posted something.
- **DC (7 of 8):** new parser for DCBOE's JSON (`cityWide/getCityWide/<year>-General-Election`). Ranked-choice
  contests have first-choice counts only until round-by-round results are posted (DCBOE says Nov 4); their titles
  say "(first-choice votes)". Oye Owolewa confirmed by hand (WFP spells it "Olowela"). Rashida Brown isn't on the
  Ward 1 ballot; marked `no` in `results_sources.csv`.
- **Massachusetts:** no source. The state's electionstats site lists only this year's two special elections and
  adds a general election after certification. There is no official election-night feed.

### 10:17am: Massachusetts by hand

- 870 races with results, WFP leading 703. All 20 Massachusetts rows are settled.
- **Where the numbers come from:** AP's counts, read in the browser from AP widgets that news sites embed and entered in
  `manual_entries.csv`. The questions came from WGBH's page (86% of expected votes, as of about 7:10am) and the
  legislative races from CBS Boston's State House and Senate widgets, which cover every district. These only change
  when re-entered.
- **Ballot questions (7):** WFP's side leads on all seven: Q1 Yes 86.0%, Q2 Yes 64.2%, Q3 No 61.2%, Q4 Yes 56.5%,
  Q5 No 52.2% (AP hasn't called it; the Yes campaign conceded), Q8 No 75.7%, Q9 Yes 67.0%.
- **Contested legislative races (5):** Lorena Betts (16th Middlesex) 68.2%; Jack Richardson (3rd Barnstable) 51.7%, 820
  ahead; Lora Wondolowski (1st Franklin) 74.1%; Tom Hendrickson (3rd Hampden) 36.4%, trailing; Shannon Teabo 46.1%,
  trailing Peter Durant. Teabo is running for the Worcester and Hampshire State Senate seat, though WFP lists her
  for State House; confirmed by hand.
- **Unopposed (4):** Celina Reyes (16th Essex), John Drinkwater (17th Middlesex), Tara Hong (18th Middlesex), Ben
  Ewen-Campen (27th Middlesex). AP posts no count for these. They're entered with votes `unopposed`, and the dashboard
  now shows "Unopposed" (new `uncontested` flag on contests, published in `wfp_results.json`).
- **Not on the ballot (4):** each lost the Sept 1 Democratic primary (per electionstats.state.ma.us): Johnnie McKnight
  (11th Hampden, to Bud Williams), Latoya Gayle (1st Suffolk Senate, to Nick Collins), Daniel Lander (Suffolk and
  Middlesex Senate, to William Brownsberger), Carey McDonald (5th Middlesex Senate, to Kate Lipper-Garabedian). Marked
  `no` in `results_sources.csv`.

### 10:31am: New York districts from county results, and an NYC fix

- 915 races with results, WFP leading 742.
- **Summed districts (40 WFP races, 34 leading):** new derived source `ny.counties` (`scrapers/elex/combine.py`). Each
  New York county source reports its share of the Assembly, Senate and U.S. House races on its ballot; when every
  county in a district has a working source, the shares are added up. District-to-county lists come from the Census
  Bureau's block equivalency files (`data/ny_district_counties.json`: Assembly 2024 lines, Senate 2022, Congress
  119th). A county source that doesn't list a district is taken to have no voters in it (the Census files include
  empty water blocks); a county with no source, or one that hasn't posted, leaves the district out. 60 districts in
  all were summed, 40 of them WFP races.
- Close or trailing among them: Chris Gallant (NY-1) 48.9%, Cait Conley (NY-17) 52.2%, Christopher Murray (SD-1)
  51.7%, Antonio Vargas (SD-3) 46.0%, Joshua Slaughter (AD-3) 51.1%, Patricia Kopp (AD-7) 45.8%, Craig Herskowitz
  (AD-12) 51.5%, Jonathan Lipe (AD-119) 47.3%, Kurtis VanWuyckhuyse (AD-134) 44.1%, Ryan Taughrin (AD-143) 50.4%,
  Thomas Carle (AD-150) 37.1%.
- **NYC parser bug, fixed:** NYC bolds the leading row (`<td style="font-weight: bold">`) and the row pattern only
  accepted bare `<td >` cells, so a leader on a single party line was dropped. Five WFP races were missing their
  candidate (Aber Kawas SD-12, Andrew Hevesi AD-28, Emily Gallagher AD-50, Illapa Sairitupac AD-65, David Siffert
  AD-66) and now show. No published NYC race changed direction: the leaders already shown ran on several lines, whose
  votes come from the "Totals by Candidate" rows.
- **Still left out:** Hochul, Adams, James and DiNapoli (statewide; no state feed) and 42 district races. The counties
  blocking the most: Albany and Onondaga (7 races each), Niagara (6), Nassau and Schenectady (5 each). See the run log
  (`ny.counties skipped ...` lines) for each district's missing counties.

### 10:44am: more New York counties

- 958 races with results, WFP leading 777. 91 New York districts are now summed from county results, 52 of them WFP
  races (44 leading); 34 New York races are still uncovered (4 statewide, 30 districts).
- **Onondaga:** Results Caster at `ongov.resultscaster.com` (linked from onondaga.gov/elections), same module as Erie.
- **Six more counties on Enhanced Voting:** Jefferson, Livingston, Madison, Ontario, Steuben, Wayne, found by probing
  all 62 counties. They have no WFP local races but complete multi-county districts (Ontario completes NY-25).
- **Nassau:** election-night results are a PDF converted to HTML (`app.nassaucountyny.gov/BOE/results/election2.html`);
  new text parser. 1,042 of 1,083 precincts as of 11:55pm.
- **Albany:** election-night PDF in the standard "Election Summary" layout; new `platforms/summary_pdf.py` using
  `pdfplumber` (added to `requirements.txt`). The county page adds its PDF links with JavaScript, so the PDF's address
  is set in `counties/ny.py`; a re-upload under a new address needs it updated.
- **Schenectady:** "Summary Results Report" HTML at `.../BOE Election Results/GE26.html` (the EL45/PE26 files are
  older elections); new parser. 101 of 102 precincts.
- **Saratoga:** numbered election-night PDFs ("BoE-GeneralElection2026-Unofficial09.pdf", highest is newest) in the
  "Statement of Votes Cast" layout; `parse_statement` in `summary_pdf.py`. Minor party lines ("No Kings") are
  recognized when they fit within the candidate's total.
- **Fix:** "County Legislature ... District 6" (Albany) was classified as a state legislature race because of the
  word "legislature"; county legislature titles are now local. No other published result changed.
- Confirmed by hand: Onondaga nicknames (Gregg Eriksen, Nicole Watts, Jo Bennett, Page Steinhardt) and Marty O'Connor
  (Saratoga's "CP Super" seat). Not on the county's ballot: Phil Dilmore (Onondaga LD-12; Neil Smith is the Democrat).
- **Still blocking districts:** Niagara (8 districts; its results site returns 403 to scripts) and rural counties with
  no readable results (Otsego, Washington, Cayuga 6 each; Delaware, Montgomery, Fulton, St. Lawrence, Herkimer,
  Chenango, Cortland 5 each).

### 10:52am: Niagara

- 972 races with results, WFP leading 782. 95 New York districts summed (55 WFP races, 46 leading); 31 New York races
  still uncovered (4 statewide, 27 districts).
- Niagara no longer uses `ny.votereporting.com` (the address that returned 403). Its results page
  (elections.niagaracounty.gov/election-results) links NTS's "Voter Information Center"
  (`vic.ntsdata.com/enr/Niagara/297/result`), backed by a public JSON API that scripts can read. New module
  `platforms/nts_vic.py`; the election id (297) is set in the source and checked against the election date.
- Added 13 Niagara local matches (all 11 county legislature and town races WFP lists, plus Doug Mooradian confirmed
  by hand) and completed NY-26 (Tim Kennedy 65.5%), AD-140 (Bill Conrad 76.1%) and AD-144 (Donna Dye Sholk 39.8%,
  trailing).
- NTS's API also has records for most of the rural counties still blocking districts (Otsego, Washington, Cayuga,
  Delaware ...), but none had a Nov 3 election near Niagara's id, and the list of a county's elections needs a login.
  They probably use NTS for voter registration only.

### Nov 4, 10:51pm: evening pull, and sites starting to block

- Candidate list re-scraped first: 1,221 rows (Tarrant County TX: Tiffany Burks and Alisa Simmons added, "Dr. Jared
  Williams" renamed Jared Williams). See `docs/candidate-changes.md`. All three are unmatched because Tarrant still
  lists no Nov 3 election on Clarity.
- 973 races with results, WFP leading 783. Vote counts changed in 405 races, mostly Colorado (75), Oregon (56),
  Connecticut (43), the summed New York districts (27), Ulster County NY (27) and Arizona (22).
- **Blocked or down this run:** New Mexico, Florida, Ohio, DC and Kenosha County now return 403 to scripts (all
  worked election night); Nassau County, Dane County and Washtenaw County timed out. A failed pull keeps the source's
  last good results, so those races still show, just not updated. Not worked around.
- **Fix:** the summed New York districts required each county's latest pull to succeed, so Nassau's timeout dropped
  21 districts (95 → 74). A county whose pull fails now contributes its last good results, like every other source;
  a county reporting no Nov 3 election still leaves its districts out.
- New: Angie Parkinson (CT HD-10, 73.0%) and Michelle Embree Ku (CT HD-106, 54.8%).
- Flipped to leading: Marie Tsaasan (Aliso Viejo D3), now 4 votes ahead; Richard Smith Savage (McMinnville Ward 3,
  OR), 27 ahead with 35.5% in a multi-candidate race.
- Flipped to trailing: Catherine Sayles (Eastchester supervisor, Westchester) 47.4%, 404 behind; Sara Duncan (49.7%,
  422 behind) and Maria Hinojos Pressey (49.8%, 181 behind), both Marion County OR, which flipped to leading
  overnight and back now.
- Still on the line: Steven Krasner (Newburgh supervisor) leads by 15, Kyle Fendrich (Dutchess LD-15) trails by 6,
  Trish Prunty (Dutchess LD-7) trails by 36. Connecticut is at 775 of 776 precincts with Mandato (+25) and Becker (+34)
  unchanged. Chris Kluwe (CA AD-72) is 2,719 behind.

### Nov 4, 11:07pm: Michigan by hand

- 985 races with results, WFP leading 794. Michigan: 17 of 19 WFP races covered; only the two Bay City Commission
  races are left (not on Bay County's report).
- The state's unofficial results (`mvic.sos.state.mi.us/votehistory/Index?type=C&electionDate=11-3-2026`, linked from
  michigan.gov's results table) show scripts a Cloudflare challenge, so they're read in the browser and entered in
  `manual_entries.csv`. Update read: 4:46pm Nov 4.
- **The state file has 82 of 83 counties; Wayne (Detroit) isn't in yet.** Every race whose district includes Wayne is
  entered as the state's 82-county numbers plus Wayne's own TotalVote results, added in code, and its title says so
  ("U.S. Senate (state's 82 counties plus Wayne County)"). Wayne is at 757 of 770 precincts for statewide races and
  100% for the districts. Without Wayne, El-Sayed was at 49.3%; with it he leads 52.5%. Gilchrist (Secretary of
  State) 53.7%, Savit (Attorney General) 52.5%, Tlaib (MI-12) 76.2%.
- Entered from the state file alone (no Wayne precincts): Lawrence (MI-7) 51.0%, Manetta (HD-58) 52.6%, Dievendorf
  (HD-77) 65.0%. HD-7 isn't in the state file at all, so it lies wholly in Wayne: Wayne's result is the whole race
  (Tonya Myers Phillips 95.1%).
- These rows don't update. When the state adds Wayne, they should be re-entered from the state file alone.

### Nov 4, 11:18pm: the 34 races with no votes

- 1,019 races with results, WFP leading 816. No race shows "Awaiting results" any more.
- **Los Angeles County (26 races): a bug since election night.** `GetElectionData` returns LA's ballot with every
  `Votes` field at 0; the counts come from a second call, `GetCounterData?electionID=4348` (one `CAND` entry per
  candidate id). Every LA pull since Nov 3 had zero votes for all 409 contests, so LA's local races sat at "Awaiting
  results". The source now reads both. Nithya Raman (LA mayor) 51.7%, Marissa Roy (city attorney) 66.5%, Estuardo
  Mazariegos (LA council) 46.3%, trailing.
- **Multnomah County and Portland (8 races): ranked-choice.** Oregon's state feed lists these contests with no
  votes. New source `or.multnomah` reads Multnomah's tabulation (rcvresults.multco.us, newest preliminary report per
  contest, RCTab summary JSON). Each candidate shows their total in the last round they were in, so the top `vote_for`
  are the tabulation's winners; titles say "(ranked-choice, round N of N)". Shannon Singleton (county chair) leads;
  Bri Williams (District 2) leads, Nathan Ong Norris eliminated third; Portland District 3: Angelita Morillo and
  Tiffany Koyama Lane elected in the count so far; District 4: Mitch Green elected, Jamey Evenstar and Jeremy
  Beausoleil Smith eliminated.
- **Matcher:** when a candidate turns up in more than one race, a race with votes now wins over a zero-vote copy
  (the state feed's copy of Multnomah's contests).
- Confirmed by hand: Helen Kreiger (WFP's spelling; LA's feed has "Krieger", same West Hollywood race).
- Still blocked or down this run: New Mexico, Florida, Ohio, DC, Kenosha (403); Nassau, Dane, Washtenaw (timeouts).
  Their last good results stay on the dashboard.
- **Why they're blocked: almost certainly location.** These runs came from a network in Mexico; every one of these
  sources worked from the US on election night. The 403s are Cloudflare challenges (Florida, Ohio, DC), an F5 firewall
  rejection (New Mexico) and Incapsula (Kenosha); Nassau, Dane and Washtenaw drop the connection outright, the usual
  sign of a country-based firewall rule. The in-app browser on the same connection gets the same treatment (Nassau
  won't load; Florida shows a real browser Cloudflare's bot check). Running from a US network should clear them.

### Nov 5, 9:55am: quiet morning

- 1,019 races with results, WFP leading 816, unchanged. Vote counts moved in only 12 races (Connecticut 10, California
  1, Maryland 1); nothing flipped.
- Run from Mexico again, so the same eight sources stayed blocked or timed out (New Mexico, Florida, Ohio, DC, Kenosha,
  Nassau, Dane, Washtenaw); their last good results stay on the dashboard.
- Most county sites haven't posted since election night. California counts mail ballots for weeks; the close
  California races (Kluwe AD-72 -2,719, Frame SD-6 -8,358, Lopez AD-68 -2,771, Tsaasan Aliso Viejo +4) haven't moved
  since Nov 4.

### Nov 7, 10:29am: California counties update

- Candidate list re-scraped first: 1,221 rows, no changes.
- 1,019 races with results, WFP leading 819 (+3). Vote counts changed in 531 races: Colorado 80, Oregon 58,
  Connecticut 33, every California county (California 31, LA 26, Orange 20, San Diego 16, Santa Clara 13, San Mateo
  11, San Bernardino 10 ...), the summed New York districts 27, Ulster 27, Pennsylvania 24, Arizona 22.
- Flipped to leading: Brad Chambers (PA HD-41), 30 ahead (50.0%); Mishaun Watkins (Lynwood council) and Stephen Post
  (West Hollywood council), both now within the seats being filled in multi-seat races.
- Closing California gaps: Jessie Lopez (AD-68) 717 behind (was 2,771), Sean Frame (SD-6) 5,171 behind (was
  8,358), Chris Kluwe (AD-72) 2,214 behind (was 2,719), Estuardo Mazariegos (LA council) 702 behind (was 1,898),
  Steven Kung (Monterey Park) 37 behind (was 62).
- Leads that grew: Brandi Mandato (CT SD-34) +231 (was +25), Marie Tsaasan (Aliso Viejo) +60 (was +4), Nancy Martiz
  (Huntington Park) +104 (was +7), Cait Conley (NY-17) 53.0%.
- Leads that shrank: Cindy Lopez (National City) +13 (was +44), Kisha Skipper (Westchester LD-15) +260 (was +999),
  Heather Buch (OR) +196 (was +697). Sara Duncan and Maria Hinojos Pressey (Marion County OR) fell further behind.
- The same eight sources are still blocked or timing out from Mexico (New Mexico, Florida, Ohio, DC, Kenosha, Nassau,
  Dane, Washtenaw).

### Nov 8, 7:05pm: Jessie Lopez pulls ahead

- 1,019 races with results, WFP leading 821 (+2). Vote counts changed in 215 races: Colorado 40, LA County 26,
  California 21, Arizona 20, Orange County 20, Westchester 19, Washington 14, Santa Clara 13, San Bernardino 10.
- Flipped to leading: Jessie Lopez (CA AD-68), 1,105 ahead (50.6%; was 717 behind); Joz Sida (Fontana mayor), 14
  ahead in a multi-candidate race (was 1,491 behind).
- Still closing: Chris Kluwe (CA AD-72) 1,701 behind (was 2,214), Estuardo Mazariegos (LA council) 417 behind (was
  702), Steven Kung (Monterey Park) 19 behind (was 37), David Ross (LA Superior Court 131) 49.7%.
- Holding: Brandi Mandato (CT SD-34) +259, Marie Tsaasan (Aliso Viejo) +58, Nancy Martiz (Huntington Park) +131,
  Kisha Skipper (Westchester LD-15) +246.
- The same eight sources are still blocked or timing out from Mexico.

### Nov 9, 2:04pm: slower updates

- 1,019 races with results, WFP leading 822 (+1). Vote counts changed in 159 races: LA County 26, Ulster County NY 26,
  Oregon 17, California 16, Georgia 15, Santa Clara 13, Arizona 10, Connecticut 10, Multnomah 8.
- Flipped to leading: Erik Poicon (Mountain View council, multi-seat), now within the seats being filled.
- Still closing: Steven Kung (Monterey Park) 10 behind (was 19), Estuardo Mazariegos (LA council) 347 behind (was
  417), David Ross (LA Superior Court 131) 49.8%. Chris Kluwe (CA AD-72) unchanged at 1,701 behind.
- Holding: Nancy Martiz (Huntington Park) +153, Kate Leon (Ulster LD-3) +54, Kim Becker (CT HD-62) +34, Bob Fernandez
  (CT HD-48) +58.
- The same eight sources are still blocked or timing out from Mexico.

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
| Clarity counties | Election linked from the county site but missing from `elections.json` | `eid=` on the source, used when the list is empty |
| South Carolina | XLSX snapshots on scvotes.gov, no precinct counts; "12AM" file is the next day | Latest link read each run; stdlib XLSX reader |
| NYC ENR | "*" marks the city's share of cross-city races | Marked partial |
| Erie Results Caster | Nov 3 election slug is `testgen`, titled "test" | Found by date; non-test titles preferred if one appears |
| NYS BOE | 403 to scripts | No source; state legislative races outside NYC stay `no_source` |
| Florida results file | Plain URL is a stale cached copy | Link (with `?v=`) read from the Downloads page each run |
| Florida measures | "No for Rejection" contains "for" | `yes_no` checks the first word first |
| Milwaukee County (WI) | Election-night page returns 403 to scripts | Manual entries |
| Kenosha County (WI) | Election id is a number in the URL (`eid=70` for Nov 3) | Hard-coded per election; the page's date is checked |
| Wayne County (MI) | County site 403s; results are on TotalVote | Scraped from `michigan.totalvote.com/Wayne` |
| Washtenaw County (MI) | Results URL includes the election (`nov2026`); precincts counted is countywide only | URL built from the election date; countywide text |
| Bay County (MI) | PDFs only | Read by hand |
| Enhanced Voting (Monroe, Rockland, Suffolk) | Fusion line named "WOR <candidate>" | Prefix stripped so the lines combine |
| Live Voter Turnout (San Diego) | No contest groups; party appended to names | State and district offices, appellate courts and numbered propositions marked partial by title |
| Live Voter Turnout (San Bernardino) | County page forwards to the results by script | Source points at the Live Voter Turnout page |
| Chautauqua (NY) | One XML file; state races filed under "New York State" | Those marked partial; place name added to town and village titles |
| Arizona | State site behind a Cloudflare challenge | Results read from Enhanced Voting's host, which the state links to |
| DC | Ranked-choice contests post first-choice counts on election night | Title says "(first-choice votes)" |
| Massachusetts | No official election-night feed; AP posts no count for unopposed races | Entered by hand from AP widgets on news sites; `unopposed` in the votes column |
| NYC ENR | Leading row's cells are bold (`<td style=...>`) | Row pattern accepts any cell attributes |
| New York districts | No readable state feed | Summed from county shares when every county in the district has a source |
| Albany County (NY) | PDF links added by JavaScript | PDF address set in the source |
| Saratoga County (NY) | Numbered PDF uploads; page headers repeat mid-contest | Highest number taken; header rows skipped |
| Nassau County (NY) | PDF rendered as HTML text runs | Text joined, page headers cut, parsed as one stream |
| Niagara County (NY) | Moved to NTS; election list needs a login | Election id set in the source, date checked |
| NM, FL, OH, DC, Kenosha (WI); Nassau, Dane, Washtenaw timeouts | Blocked on Nov 4 evening runs made from Mexico; worked from the US | Last good results kept; run from a US network |
| Michigan SoS results | Cloudflare challenge to scripts; Wayne posted last | Entered by hand: state's 82 counties plus Wayne's TotalVote share |
| Los Angeles County | Ballot and counts come from separate calls | `GetElectionData` for the ballot, `GetCounterData` for votes |
| Multnomah County (OR) | Ranked-choice contests have no votes in the state feed | County tabulation JSON; last-round totals |
| Oregon | Vote by mail; precincts-reporting stays at 0 while votes come in | Shown as reported; worth replacing with a count or hiding |

## Still open

- South Carolina, three Texas counties, two New Jersey counties and five California Clarity counties
  hadn't posted a Nov 3 election by 11:10pm.
- Wisconsin: 9 of 29 races. Still missing: the statewide races and questions, SD-5, 7, 17, 21, 31, AD-13, 21, 51,
  53, 61–63, 73, 90, 93 (multi-county, or counties that block scripts or post PDFs).
- Michigan: 17 of 19 races. The statewide and district races are hand-entered (state's 82 counties plus Wayne) and
  need re-entering once the state adds Wayne. The two Bay City Commission races aren't on Bay County's report.
- Kentucky and Maine have no source; they need manual entries.
- Massachusetts is entered by hand (AP as of about 7–10am Nov 4) and only updates when re-entered; Q5 and the
  3rd Barnstable race are close.
- DC's ranked-choice rounds: re-check after DCBOE posts them and drop the "(first-choice votes)" label then.
- Milwaukee's six races only update when re-entered by hand.
- New York counties still without a source: Onondaga (21; ongov.net doesn't answer scripts, and it isn't on Enhanced
  Voting), Niagara (11; `ny.votereporting.com` returns 403), Albany (5), Saratoga (3) and single races elsewhere.
- California counties still without a source: Alameda (15), San Francisco (13, blocked), Riverside (11, blocked),
  Santa Barbara (7), Kern (5), Fresno and Tulare (4 each), Santa Cruz and Stanislaus (3 each).
- Eight California propositions stay in review: several county sources carry their own share, and the state API's
  copy doesn't match on its own.
- New York districts are summed from county shares (`ny.counties`); 30 WFP district races still lack a county source,
  all because of small rural counties with no readable results (Otsego, Washington, Cayuga, Delaware ...). Wisconsin could reuse `combine.py` with its own mapping.
