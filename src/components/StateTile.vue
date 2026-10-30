<script setup lang="ts">
import { computed } from 'vue'
import type { StateTileData } from '../data/types'
import Tile, { type TileTone } from './Tile.vue'

const props = defineProps<{ state: StateTileData; selected: boolean }>()
defineEmits<{ select: [abbreviation: string] }>()

// Notch corners per the spec: federal on top, state legislature on the bottom.
const notches = computed(() => ({
  topLeft: props.state.has_federal_house,
  topRight: props.state.has_federal_senate,
  bottomLeft: props.state.has_state_house,
  bottomRight: props.state.has_state_senate,
}))

const tone = computed<TileTone>(() =>
  props.selected ? 'active' : props.state.has_wfp_endorsements ? 'highlight' : 'muted',
)

const ariaLabel = computed(() => {
  const n = props.state.endorsement_count
  return n
    ? `${props.state.state_name}: ${n} endorsement${n === 1 ? '' : 's'}`
    : `${props.state.state_name}: no WFP endorsements`
})
</script>

<template>
  <Tile
    :label="state.state_abbreviation"
    :notches="notches"
    :tone="tone"
    :disabled="!state.has_wfp_endorsements"
    :pressed="state.has_wfp_endorsements ? selected : undefined"
    :aria-label="ariaLabel"
    @click="$emit('select', state.state_abbreviation)"
  />
</template>
