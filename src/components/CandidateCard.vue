<script setup lang="ts">
import { computed, ref } from 'vue'
import { displayStatus, resultFor } from '../data/results'
import type { Candidate } from '../data/types'
import ResultDetail from './ResultDetail.vue'

const props = defineProps<{ candidate: Candidate }>()

const isMeasure = computed(() => props.candidate.office_category === 'Ballot Measure')
const chips = computed(() =>
  [props.candidate.district, props.candidate.region].filter(Boolean),
)

const result = computed(() => resultFor(props.candidate))
const status = computed(() => displayStatus(props.candidate))
const expanded = ref(false)

/** The pill in the card's corner. We report counts; we don't call races. */
const pill = computed(() => {
  const r = result.value
  switch (status.value) {
    case 'leading':
    case 'trailing':
      if (r?.uncontested) return { text: 'Unopposed', class: 'bg-wfp-purple text-white' }
      return r?.status === 'final'
        ? { text: 'Final', class: 'bg-wfp-purple text-white' }
        : { text: 'Counting', class: 'bg-wfp-marigold text-neutral-900' }
    case 'awaiting':
      return { text: 'Awaiting results', class: 'bg-wfp-gray text-neutral-700' }
    default:
      return null
  }
})

const wfpChoice = computed(() => result.value?.choices?.find((c) => c.is_wfp))
const hasVotes = computed(() => status.value === 'leading' || status.value === 'trailing')

/** Shown instead of results when a race isn't tracked. */
const quietNote = computed(() =>
  status.value === 'not_on_ballot'
    ? 'Not on the Nov 3 ballot'
    : status.value === 'not_tracked'
      ? 'Results not tracked yet'
      : null,
)

const percent = (pct: number | null | undefined) => (pct == null ? '–' : `${pct.toFixed(1)}%`)
</script>

<template>
  <li class="rounded border-l-4 border-wfp-orange bg-white px-3 py-2 shadow-sm ring-1 ring-black/5">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="font-semibold leading-snug lg:text-lg">{{ candidate.name }}</p>
        <p v-if="!isMeasure" class="text-sm leading-snug text-neutral-600 lg:text-base">{{ candidate.office }}</p>
        <div v-if="chips.length" class="mt-1 flex flex-wrap gap-1">
          <span
            v-for="chip in chips"
            :key="chip"
            class="rounded-sm bg-wfp-gray px-1.5 py-0.5 text-xs text-neutral-700 lg:text-sm"
          >
            {{ chip }}
          </span>
        </div>
      </div>
      <div class="flex shrink-0 flex-col items-end gap-1">
        <span
          v-if="isMeasure"
          class="rounded px-2 py-0.5 font-headline text-base font-bold uppercase lg:text-lg"
          :class="candidate.position === 'Yes' ? 'bg-wfp-purple text-white' : 'bg-wfp-orange text-white'"
        >
          Vote {{ candidate.position }}
        </span>
        <span
          v-if="pill"
          class="rounded-full px-2 py-0.5 font-headline text-sm font-bold uppercase tracking-wide lg:text-base"
          :class="pill.class"
        >
          {{ pill.text }}
        </span>
      </div>
    </div>

    <!-- Results summary -->
    <p v-if="quietNote" class="mt-1.5 text-xs text-neutral-500 lg:text-sm">{{ quietNote }}</p>
    <button
      v-else-if="result"
      type="button"
      class="mt-1.5 flex w-full items-center gap-2 rounded text-left text-sm hover:bg-[#f7f6f2] lg:text-base"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <strong v-if="result.uncontested" class="text-wfp-purple">Unopposed on the ballot</strong>
      <template v-else-if="hasVotes && wfpChoice">
        <strong class="tabular-nums">{{ percent(wfpChoice.pct) }}</strong>
        <span v-if="isMeasure" class="text-neutral-600">{{ wfpChoice.name }}</span>
        <span
          class="font-semibold"
          :class="status === 'leading' ? 'text-wfp-purple' : 'text-wfp-orange'"
        >
          {{ status === 'leading' ? '▲ Leading' : '▼ Trailing' }}
        </span>
      </template>
      <span v-else class="text-neutral-500">No votes reported yet</span>
      <span v-if="!result.uncontested && result.reporting?.pct != null" class="text-neutral-500">
        · {{ percent(result.reporting.pct) }} reporting
      </span>
      <!-- Some feeds only say how many counties have posted, which isn't a share of the vote counted. -->
      <span v-else-if="!result.uncontested && result.reporting?.text" class="text-neutral-500">
        · {{ result.reporting.text }}
      </span>
      <span class="ml-auto text-neutral-500" aria-hidden="true">{{ expanded ? '▴' : '▾' }}</span>
      <span class="sr-only">{{ expanded ? 'Hide' : 'Show' }} all results</span>
    </button>

    <ResultDetail v-if="expanded && result" :result="result" />
  </li>
</template>
