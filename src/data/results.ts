import rawResults from '../../data/results/wfp_results.json'
import { CANDIDATES } from './candidates'
import type { Candidate, CandidateResult, DisplayStatus, ResultsFile } from './types'

const data = rawResults as unknown as ResultsFile

export const RESULTS_GENERATED_AT = data.generated_at

/** Results by candidate id. An entry whose name doesn't match is from an older candidates.json and is dropped. */
const RESULTS = new Map<number, CandidateResult>()
const stale: string[] = []
for (const c of CANDIDATES) {
  const r = data.results[String(c.id)]
  if (!r) continue
  if (r.name && r.name !== c.name) stale.push(`${c.id}: ${c.name} ≠ ${r.name}`)
  else RESULTS.set(c.id, r)
}
if (stale.length)
  console.warn('wfp_results.json was built from an older candidates.json; run scrape_results.py match:', stale)

export function resultFor(candidate: Candidate): CandidateResult | undefined {
  return RESULTS.get(candidate.id)
}

export function displayStatus(candidate: Candidate): DisplayStatus {
  const r = resultFor(candidate)
  if (!r || r.status === 'no_source' || r.status === 'unmatched') return 'not_tracked'
  if (r.status === 'not_on_ballot') return 'not_on_ballot'
  if (r.wfp_leading === true) return 'leading'
  if (r.wfp_leading === false) return 'trailing'
  return 'awaiting'
}

export interface StatusInfo {
  status: DisplayStatus
  label: string
}

/** Filter order and labels. */
export const STATUSES: StatusInfo[] = [
  { status: 'leading', label: 'Leading' },
  { status: 'trailing', label: 'Trailing' },
  { status: 'awaiting', label: 'Awaiting results' },
  { status: 'not_tracked', label: 'Not tracked yet' },
  { status: 'not_on_ballot', label: 'Not on Nov 3 ballot' },
]
