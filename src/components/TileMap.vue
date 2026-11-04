<script setup lang="ts">
import { GRID_COLUMNS, GRID_ROWS } from '../data/stateGrid'
import type { StateTileData } from '../data/types'
import StateTile from './StateTile.vue'

defineProps<{
  states: StateTileData[]
  selected: string | null
  /** State names with at least one endorsement matching the filters; the rest are drawn faded. */
  matching: Set<string>
}>()
defineEmits<{ select: [abbreviation: string] }>()
</script>

<template>
  <div
    class="grid gap-1 sm:gap-1.5"
    :style="{
      gridTemplateColumns: `repeat(${GRID_COLUMNS}, minmax(0, 1fr))`,
      gridTemplateRows: `repeat(${GRID_ROWS}, auto)`,
    }"
    role="group"
    aria-label="Filter by state"
  >
    <div
      v-for="state in states"
      :key="state.state_abbreviation"
      :style="{ gridColumn: state.x, gridRow: state.y }"
    >
      <StateTile
        :state="state"
        :selected="selected === state.state_abbreviation"
        :faded="!matching.has(state.state_name)"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>
