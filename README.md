# WFP Candidate Dashboard

A dashboard of Working Families Party 2026 endorsements: a tile grid map of the
50 states + DC on the left (click a state to filter), office-type checkboxes
below it, and the matching candidates and ballot measures on the right. The
design spec is in [wfp-candidate-dashboard.md](wfp-candidate-dashboard.md).

## Data

`candidates.json` / `candidates.csv` are produced by the scraper:

```bash
python3 scrape_wfp_candidates.py
```

The dashboard bundles `candidates.json` at build time, so rebuild after re-scraping.

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
| `src/data/candidates.ts` | Loads `candidates.json` and derives each state's `has_*` tile flags |

## Deploying to GitHub Pages

`.github/workflows/deploy.yml` builds and publishes `dist/` on every push to
`main`. In the repository's **Settings → Pages**, set **Source** to
**GitHub Actions**.
