---
name: update-results
description: Run the WFP election results scrapers, compare against the previous run, and update the docs and dashboard. Use when asked to "run the results scrapers", "pull results again", "check for late updates", or to refresh election results in this repo.
---

# Update election results

Runs every results source, reports what changed since the last run, records the run in
`docs/election-results-scraper-notes.md`, and rebuilds the dashboard. Work from the repo root.

## Ground rules

- **Never commit or push.** The user manages commits. Leave changes in the working tree.
- **Don't get around sites that block scripts** (403s, bot challenges). Read them in the browser and enter results
  by hand in `data/results/manual_entries.csv`, as the existing hand entries do. The one approved exception is
  Florida's results host (`config.UNVERIFIED_TLS_HOSTS`, an expired certificate).
- Scraped data lives in `data/`, docs in `docs/`. `docs/results_sources.csv` uses CRLF line endings: write it with
  `csv.DictWriter(..., lineterminator='\r\n')`.

## Steps

### 1. Snapshot the current results

```bash
cp data/results/wfp_results.json "$TMPDIR/wfp_results.before.json"
```

Use the session's scratchpad directory instead of `$TMPDIR` when there is one.

### 2. Run the scrapers

```bash
.venv/bin/python scrapers/scrape_results.py run
```

This pulls all sources (about 2 minutes), rebuilds the New York county sums, rematches and publishes
`data/results/wfp_results.json`. The run id (UTC) and log path are printed at the end
(`logs/results/<run id>.log`). Read the per-source lines for `error`, `blocked` and `not_published`.

If the user also asked to run the candidate scraper, do that first (`scrapers/scrape_wfp_candidates.py`) and record
changes in `docs/candidate-changes.md` and `docs/results_sources.csv`.

### 3. Compare with the snapshot

```bash
.venv/bin/python .claude/skills/update-results/compare.py "$TMPDIR/wfp_results.before.json"
```

The script prints:
- totals: races with results and WFP leading, before and after
- sources that aren't ok
- vote-count changes by source
- status changes and new races
- flips: WFP moved into or out of the lead
- closing and widening margins (within 5% of the vote)
- the hand entries

Margins are WFP's votes minus the rival across the winning line, so `+` means leading.

Look into anything surprising before writing it up. Examples: a source that newly errors, a count that went down,
or a race that changed status.

### 4. Check the hand entries

Hand entries only change when re-entered. The end of the comparison output lists every hand-entered contest:
- oldest first, with its "as of" time
- `[re-entry noted]` when its note asks for one (for example "re-enter after the Nov 13 count")

Mention the stale or due ones in the summary. Re-enter them only if the user asks. Re-entering means:
- read the page in the browser
- update the rows in `data/results/manual_entries.csv`
- run `.venv/bin/python scrapers/scrape_results.py run --sources manual`

### 5. Update the notes

In `docs/election-results-scraper-notes.md`. Times are Eastern; run ids are UTC.

- **Summary table:** add a row after the last one, with the time (ET), races with results, WFP leading, and what was
  new. Use "(none new; N counts changed; ...)" when no source was added.
  ```
  | Nov 12, 8:37pm | 1,085 | 879 | (none new; 363 counts changed; Kluwe and Currey Nunez flip to leading) |
  ```
- **Dated section:** add `### <Mon DD>, <time>: <short title>` just before the `---` above
  `## Feed quirks worth remembering`. Cover:
  - which sources ran, and any that failed or are still unpublished
  - totals and the top sources by changed counts
  - flipped races
  - the notable closing and widening races, with margins as "N ahead (was M)" or "N behind (was M)"
  - very close races that didn't move
- **Feed quirks table:** add a row for any new quirk and its fix.
- **"Still open":** update the list if anything was resolved or newly broke.

### 6. Rebuild the dashboard

```bash
npm run build
```

This writes `dist/`. If any code under `scrapers/` changed during the run, also run
`.venv/bin/python -m pytest -q tests`.

### 7. Report

Give the user:
- the totals
- flips, closing races and widening leads, with names and margins
- sources that failed or are still missing
- hand entries due for re-entry

Say that the notes and `dist/` are updated and that nothing is committed.
