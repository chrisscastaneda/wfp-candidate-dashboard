# WFP Candidate Dashboard

A dashboard of Working Families Party 2026 endorsements: a tile grid map of the
50 states + DC on the left (click a state to filter), office-type checkboxes
below it, and the matching candidates and ballot measures on the right. The
design spec is in [prompts/wfp-candidate-dashboard.md](prompts/wfp-candidate-dashboard.md).

Live version: [chrisscastaneda.github.io/wfp-candidate-dashboard](https://chrisscastaneda.github.io/wfp-candidate-dashboard/)

## Project layout

| Folder | Contents |
|---|---|
| `scrapers/` | Python scripts that collect data (standard library only) |
| `data/` | Everything the scrapers produce. Scrapers write here by default, wherever they're run from |
| `docs/` | Project documentation, such as the [election results source map](docs/election-results-sources.md) |
| `src/` | The dashboard (Vue + TypeScript) |

New scrapers go in `scrapers/` and write their output to `data/`; new documentation goes in `docs/`.

## Data

`data/candidates.json` / `data/candidates.csv` are produced by the scraper:

```bash
python3 scrapers/scrape_wfp_candidates.py
```

Pass a folder as the first argument to write somewhere else. The dashboard
bundles `data/candidates.json` at build time, so rebuild after re-scraping.

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
