import rawData from '../../data/candidates.json'
import { CATEGORIES } from './categories'
import { STATE_GRID } from './stateGrid'
import type { Candidate, CandidateFile, StateTileData } from './types'

const data = rawData as CandidateFile

export const CANDIDATES: Candidate[] = data.candidates
export const SCRAPED_AT = data.scraped_at
export const SOURCE_URL = data.source

/** Tile attributes for every state on the grid, derived from the candidate data. */
export const STATE_TILES: StateTileData[] = STATE_GRID.map((entry) => {
  const rows = CANDIDATES.filter((c) => c.state === entry.state_name)
  const present = new Set(rows.map((c) => c.office_category))
  const tile = {
    ...entry,
    endorsement_count: rows.length,
    has_wfp_endorsements: rows.length > 0,
  } as StateTileData
  for (const { category, flag } of CATEGORIES) tile[flag] = present.has(category)
  return tile
})

/** Candidate states missing from the grid would silently never show on the map. */
const gridNames = new Set(STATE_GRID.map((s) => s.state_name))
const unmapped = [...new Set(CANDIDATES.map((c) => c.state))].filter((s) => !gridNames.has(s))
if (unmapped.length) console.warn('States in data/candidates.json missing from STATE_GRID:', unmapped)
