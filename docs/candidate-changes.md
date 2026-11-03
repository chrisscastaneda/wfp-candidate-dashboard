# Candidate list changes

A running log of what changes on [workingfamilies.org/candidates](https://workingfamilies.org/candidates/)
between scrapes of `data/candidates.json`. Newest entries first.

Each entry compares a scrape with the one before it, keyed on state + name + office. Office names rewritten by the
scraper's `OFFICE_OVERRIDES` are compared after the rewrite, so they don't show up as changes. When a change also
affects `docs/results_sources.csv`, the entry says so.

---

## Nov 3, 2026 (early morning): 1,216 → 1,219 rows

Scraped 2026-11-03 08:11 UTC (3:11am ET, election day), compared with the 00:18 UTC scrape. 4 rows were added and
1 removed, all in Wisconsin, which went from 26 rows to 29.

### Added (4)

- **Wisconsin ballot measures (3).** WFP's position is **No** on all three:
  - Question 1, Partial Veto Referendum
  - Question 2, Freedom to Gather in Places of Worship During an Emergency Referendum
  - Question 3, Governmental Entity Discrimination Prohibited Referendum
- **Robyn Vining, State Senate District 5.** This replaces her District 35 listing (removed below), so it's likely a
  correction on WFP's site, not a new endorsement.

### Removed (1)

- Robyn Vining, State Senate District 35 (now District 5, above)

### Notes

- These are WFP's first Wisconsin ballot measures. The candidate scraper's run log reported the same changes, so
  WFP made them some time on Nov 2.
- Vining's new row moves up in the list, so four Wisconsin State Senate rows got new ids: Larson, Jacobson, Jung and
  Smith (1127–1130 → 1128–1131).
- `docs/results_sources.csv` was updated to match:
  - Vining's row now reads District 5.
  - The three questions were added. Like the rest of Wisconsin they have no election-night feed, so they're
    `no_source` until the certified canvass.
  - Ids were realigned with the new scrape.
- `data/results/wfp_results.json` was re-published (`scrape_results.py match`), so its ids match the new
  `candidates.json`.

---

## Nov 2, 2026 (evening): 1,194 → 1,216 rows

Scraped 2026-11-03 00:18 UTC, compared with the earlier Nov 2 scrape. 36 rows were added and 14 removed. No existing
endorsement changed office or category.

The earlier Nov 2 `candidates.json` wasn't kept, so this comparison used `docs/results_sources.csv` as built from that
scrape. All 36 added rows were given results sources, and the 14 removed rows were dropped from
`results_sources.csv`.

### Added (36)

**New Mexico (32).** The state went from 11 rows to 38.

- Statewide:
  - Stephanie Garcia Richard, Lieutenant Governor
  - Juan De Jesus Sanchez III, Commissioner of Public Lands. This replaces "Juan De Jesus Sanchez" (removed below),
    so it's likely a rename, not a new endorsement.
  - Gabe Vasquez, US House District 2
- County Commission (6):
  - Eric Olivas, Bernalillo District 5
  - Cari Power, Socorro District 1
  - Daisy Maldonado, Doña Ana District 1
  - Elouise Brown, San Juan District 2
  - Paul Madrid, Sandoval District 1
  - Frank Smith, Sandoval District 3
- State House (23):

  | District | Candidate |
  |---|---|
  | 8 | Katherine Gauer |
  | 10 | G. Andres Romero |
  | 11 | Javier Martinez |
  | 14 | Miguel Garcia |
  | 18 | Marianna Anaya |
  | 19 | Janelle Anyanonu |
  | 24 | Liz Thomson |
  | 25 | Cristina Parajón |
  | 26 | Eleanor Chávez |
  | 28 | Pamelya Herndon |
  | 29 | Joy Garratt |
  | 30 | Elizabeth Diane Torrez-Velasquez |
  | 32 | Laura Parra |
  | 35 | Angelica Rubio |
  | 38 | David Mooney |
  | 42 | Kristina Ortez |
  | 44 | Kathleen Cates |
  | 45 | Linda Serrato |
  | 46 | Andrea Romero |
  | 47 | Reena Szczepanski |
  | 53 | Sarah Silva |
  | 60 | Luke Jungmann |
  | 68 | Charlotte Little |

**Elsewhere (4):**

- Arizona: Junelle Cavero, State House District 11
- Georgia: Gabriel Sanchez, State House District 42
- Colorado: Longmont Amendments 3C and 3D. These look like renames of Amendments 1 and 2 (removed below), which
  probably got their official ballot letters.

### Removed (14)

**New Mexico (5):**

- Yanira Gurrola, State House District 16
- Yolanda Jaramillo, State House District 41
- Michelle "Paulene" Abeyta, State House District 69
- Anita Gonzales, State House District 70
- Juan De Jesus Sanchez, Commissioner of Public Lands (renamed, above)

**Delaware (5).** This is a different set of five from the ones added in the earlier Nov 2 scrape, which are all
still listed.

- Shané Darby, State House District 1
- Will Imbrie-Moore, State House District 19
- Adriana Bohm, State Senate District 1
- Keonna Watson, State Senate District 12
- Syam Kosigi, New Castle County Council District 5

**Elsewhere (4):**

- Arizona: Jacob Martinez, State House LD 9
- Georgia: Adrienne Simmons, Gwinnett County School Board District 4
- Colorado: Longmont Amendments 1 and 2 (renamed, above)

### Notes

- **New Mexico** more than tripled in a day, and the new rows include House Speaker Javier Martinez. That looks like
  WFP posting its New Mexico slate late, not a scraper glitch. The scraper reads every state the same way, and no
  other state's count jumped.
- **Delaware** had five races added earlier on Nov 2 and five different races removed in this scrape. The removals
  may be WFP cleaning up candidates who lost the primary or withdrew. Worth checking with WFP.
- The copy of `data/candidates.json` in git at the time was the Oct 30 scrape (1,189 rows).
