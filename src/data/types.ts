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
