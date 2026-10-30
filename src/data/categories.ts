import type { OfficeCategory, StateTileData } from './types'

type CategoryFlag = Exclude<
  {
    [K in keyof StateTileData]: K extends `has_${string}` ? K : never
  }[keyof StateTileData],
  'has_wfp_endorsements'
>

export interface CategoryInfo {
  category: OfficeCategory
  label: string
  /** The StateTileData flag that is true when a state has this category. */
  flag: CategoryFlag
}

/** Display order, top of the ballot first. */
export const CATEGORIES: CategoryInfo[] = [
  { category: 'Federal Senate', label: 'U.S. Senate', flag: 'has_federal_senate' },
  { category: 'Federal House', label: 'U.S. House', flag: 'has_federal_house' },
  { category: 'State Executive', label: 'State Executive', flag: 'has_state_executive' },
  { category: 'State Senate', label: 'State Senate', flag: 'has_state_senate' },
  { category: 'State House', label: 'State House', flag: 'has_state_house' },
  { category: 'Judicial', label: 'Judicial', flag: 'has_judicial' },
  { category: 'Local Office', label: 'Local Office', flag: 'has_local_office' },
  { category: 'Ballot Measure', label: 'Ballot Measures', flag: 'has_ballot_measure' },
]

export const CATEGORY_ORDER = new Map(CATEGORIES.map((c, i) => [c.category, i]))
