<script setup lang="ts">
import { computed } from 'vue'
import type { Candidate } from '../data/types'

const props = defineProps<{ candidate: Candidate }>()

const isMeasure = computed(() => props.candidate.office_category === 'Ballot Measure')
const chips = computed(() =>
  [props.candidate.district, props.candidate.region].filter(Boolean),
)
</script>

<template>
  <li class="flex items-start justify-between gap-3 rounded border-l-4 border-wfp-orange bg-white px-3 py-2 shadow-sm ring-1 ring-black/5">
    <div class="min-w-0">
      <p class="font-semibold leading-snug">{{ candidate.name }}</p>
      <p v-if="!isMeasure" class="text-sm leading-snug text-neutral-600">{{ candidate.office }}</p>
      <div v-if="chips.length" class="mt-1 flex flex-wrap gap-1">
        <span
          v-for="chip in chips"
          :key="chip"
          class="rounded-sm bg-wfp-gray px-1.5 py-0.5 text-xs text-neutral-700"
        >
          {{ chip }}
        </span>
      </div>
    </div>
    <span
      v-if="isMeasure"
      class="shrink-0 rounded px-2 py-0.5 font-headline text-base font-bold uppercase"
      :class="candidate.position === 'Yes' ? 'bg-wfp-purple text-white' : 'bg-wfp-orange text-white'"
    >
      Vote {{ candidate.position }}
    </span>
  </li>
</template>
