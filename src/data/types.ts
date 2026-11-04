export type OfficeCategory =
  | 'Federal Senate'
  | 'Federal House'
  | 'State Executive'
  | 'State Senate'
  | 'State House'
  | 'Judicial'
  | 'Local Office'
  | 'Ballot Measure'

export type OfficeLevel = 'Federal' | 'State' | 'Local' | 'Ballot'

/** One row of data/candidates.json (a candidate or a ballot measure). */
export interface Candidate {
  id: number
  name: string
  office: string
  office_category: OfficeCategory
  office_level: OfficeLevel
  is_federal: boolean
  is_state: boolean
  is_local: boolean
  /** "Endorsed" for candidates, "Yes"/"No" for ballot measures. */
  position: string
  district: string
  state: string
  state_slug: string
  region: string
  state_wfp_page: string
  source_url: string
}

export interface CandidateFile {
  source: string
  scraped_at: string
  count: number
  candidates: Candidate[]
}

/** A state's place on the tile grid map (1-based; 1,1 is the northwest corner). */
export interface StateGridEntry {
  state_name: string
  state_abbreviation: string
  x: number
  y: number
}

/** Endorsement attributes a state tile reflects. */
export interface StateTileData extends StateGridEntry {
  has_wfp_endorsements: boolean
  has_federal_house: boolean
  has_federal_senate: boolean
  has_state_house: boolean
  has_state_senate: boolean
  has_state_executive: boolean
  has_judicial: boolean
  has_local_office: boolean
  has_ballot_measure: boolean
  endorsement_count: number
}

/** Endorsement statuses in data/results/wfp_results.json (see docs/election-results-scraper-plan.md). */
export type ResultStatus = 'awaiting' | 'counting' | 'final' | 'not_on_ballot' | 'no_source' | 'unmatched'

export interface ResultChoice {
  name: string
  party: string | null
  votes: number
  pct: number | null
  is_wfp: boolean
}

/** One endorsement's entry in wfp_results.json. Contest fields are absent unless a race was matched. */
export interface CandidateResult {
  name: string
  status: ResultStatus
  match_status: string
  note?: string
  source?: string
  /** Who publishes the results, and their public page for this race's election. */
  source_name?: string | null
  source_url?: string | null
  contest?: string
  scope?: string
  reporting?: { pct: number | null; text: string | null }
  updated_at?: string | null
  wfp_choice?: string
  /** Whether WFP's choice is in a winning position; null before any votes. Not a race call. */
  wfp_leading?: boolean | null
  choices?: ResultChoice[]
}

export interface ResultsFile {
  election_date: string
  generated_at: string
  run_id: string
  results: Record<string, CandidateResult>
}

/** What the dashboard shows and filters by, derived from a result. */
export type DisplayStatus = 'leading' | 'trailing' | 'awaiting' | 'not_tracked' | 'not_on_ballot'
