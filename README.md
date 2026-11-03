# WFP Candidate Dashboard

A dashboard of Working Families Party 2026 endorsements: a tile grid map of the
50 states + DC on the left (click a state to filter), office-type checkboxes
below it, and the matching candidates and ballot measures on the right. The
design spec is in [prompts/wfp-candidate-dashboard.md](prompts/wfp-candidate-dashboard.md).

Live version: [chrisscastaneda.github.io/wfp-candidate-dashboard](https://chrisscastaneda.github.io/wfp-candidate-dashboard/)

## Project layout

| Folder | Contents |
|---|---|
| `scrapers/` | Python scripts that collect data. `scrapers/elex/` is the election results package |
| `data/` | Everything the scrapers produce. Scrapers write here by default, wherever they're run from |
| `docs/` | Project documentation, such as the [election results source map](docs/election-results-sources.md) |
| `logs/` | A log for every scraper run (git-ignored) |
| `tests/` | Results scraper tests, run offline against saved feed responses in `tests/fixtures/` |
| `src/` | The dashboard (Vue + TypeScript) |

New scrapers go in `scrapers/` and write their output to `data/`; new documentation goes in `docs/`.

## Data

`data/candidates.json` / `data/candidates.csv` are produced by the scraper:

```bash
python3 scrapers/scrape_wfp_candidates.py
```

Pass a folder as the first argument to write somewhere else. The dashboard
bundles `data/candidates.json` at build time, so rebuild after re-scraping.
Each run is logged to `logs/candidates/`, including the rows added and removed
since the previous scrape (handy for [docs/candidate-changes.md](docs/candidate-changes.md)).

### Election results

`scrapers/scrape_results.py` pulls official results feeds, matches them to the
endorsements, and writes `data/results/wfp_results.json` for the dashboard. The
design and election-night runbook are in
[docs/election-results-scraper-plan.md](docs/election-results-scraper-plan.md).
It needs a virtualenv:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scrapers/scrape_results.py                  # pull everything once
.venv/bin/python scrapers/scrape_results.py --states CA,PA   # some states
.venv/bin/python scrapers/scrape_results.py --watch 5        # every 5 minutes until Ctrl-C
.venv/bin/python scrapers/scrape_results.py list             # sources and their last status
.venv/bin/python scrapers/scrape_results.py match            # re-match after editing matches.csv
.venv/bin/python scrapers/scrape_results.py manual-template  # rows to fill in by hand
.venv/bin/python -m pytest                                   # tests (offline)
```

| File in `data/results/` | What it is |
|---|---|
| `wfp_results.json` | The dashboard's file: one entry per endorsement, keyed by candidate `id` |
| `matches.csv` | Which contest and choice each endorsement matched. Review `needs_review` rows; set `status` to `confirmed`, or fix the ids and set `method` to `manual`. The matcher never changes those rows |
| `manual_entries.csv` | Hand-entered results for races no scraper covers. Add a row per candidate (same `contest_id`) and fill in `votes` |
| `latest/<source>.json` | Newest normalized contests from each source |
| `history/` | A snapshot each time a source's contests change (git-ignored) |

## Development

Vue 3 + TypeScript + Tailwind CSS v4, built with Vite.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-checks, then writes dist/index.html
```

`npm run build` produces a single self-contained `dist/index.html` (JS, CSS and
data inlined). It works when opened straight from disk or served from any static
host. Only the Google Fonts stylesheet is loaded from the network.

## Components

| File | Role |
|---|---|
| `src/components/Tile.vue` | Generic square tile: centered label, border, four toggleable corner notches, `highlight`/`muted`/`active` tones |
| `src/components/StateTile.vue` | Maps a state's endorsement flags onto a `Tile` (notches: U.S. House ↖, U.S. Senate ↗, State House ↙, State Senate ↘) |
| `src/components/TileMap.vue` | Lays state tiles out on the 11×8 grid from `src/data/stateGrid.ts` |
| `src/components/MapLegend.vue` | Explains the notches |
| `src/components/CategoryToggles.vue` | Office-type checkboxes with counts |
| `src/components/CandidateList.vue` / `CandidateCard.vue` | Results grouped by state, then office type |
| `src/data/candidates.ts` | Loads `data/candidates.json` and derives each state's `has_*` tile flags |

## Deploying to GitHub Pages

`.github/workflows/deploy.yml` builds and publishes `dist/` on every push to
`main`. In the repository's **Settings → Pages**, set **Source** to
**GitHub Actions**.
