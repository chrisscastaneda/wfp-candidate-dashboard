<script setup lang="ts">
import { computed, ref } from 'vue'
import AboutDialog from './components/AboutDialog.vue'
import CandidateList from './components/CandidateList.vue'
import CategoryToggles from './components/CategoryToggles.vue'
import MapLegend from './components/MapLegend.vue'
import StatusToggles from './components/StatusToggles.vue'
import TileMap from './components/TileMap.vue'
import { CATEGORIES } from './data/categories'
import { CANDIDATES, SCRAPED_AT, SOURCE_URL, STATE_TILES } from './data/candidates'
import { displayStatus, RESULTS_GENERATED_AT, STATUSES } from './data/results'
import type { DisplayStatus, OfficeCategory } from './data/types'

const about = ref<InstanceType<typeof AboutDialog> | null>(null)
const selectedState = ref<string | null>(null)
const enabledCategories = ref(new Set<OfficeCategory>(CATEGORIES.map((c) => c.category)))
const enabledStatuses = ref(new Set<DisplayStatus>(STATUSES.map((s) => s.status)))
const search = ref('')

const selectedTile = computed(
  () => STATE_TILES.find((s) => s.state_abbreviation === selectedState.value) ?? null,
)

function selectState(abbreviation: string) {
  selectedState.value = selectedState.value === abbreviation ? null : abbreviation
}

/** Rows in the selected state (or everywhere), before category and search filters. */
const inScope = computed(() =>
  selectedTile.value
    ? CANDIDATES.filter((c) => c.state === selectedTile.value!.state_name)
    : CANDIDATES,
)

const categoryCounts = computed(() => {
  const counts = new Map<OfficeCategory, number>()
  for (const c of inScope.value) counts.set(c.office_category, (counts.get(c.office_category) ?? 0) + 1)
  return counts
})

const statusCounts = computed(() => {
  const counts = new Map<DisplayStatus, number>()
  for (const c of inScope.value) {
    const s = displayStatus(c)
    counts.set(s, (counts.get(s) ?? 0) + 1)
  }
  return counts
})

const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return inScope.value.filter(
    (c) =>
      enabledCategories.value.has(c.office_category) &&
      enabledStatuses.value.has(displayStatus(c)) &&
      (!q || [c.name, c.office, c.district, c.region].some((f) => f.toLowerCase().includes(q))),
  )
})

const scrapedDate = new Date(SCRAPED_AT).toLocaleDateString('en-US', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})
const resultsTime = new Date(RESULTS_GENERATED_AT).toLocaleString('en-US', {
  month: 'long',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})
</script>

<template>
  <div class="flex min-h-dvh flex-col lg:h-dvh">
    <header class="flex items-center justify-between gap-4 bg-wfp-orange px-4 py-3 text-white sm:px-6">
      <h1 class="font-headline text-2xl leading-none font-bold uppercase tracking-wide sm:text-3xl">
        2026 WFP Election Results Dashboard
      </h1>
      <button
        type="button"
        class="shrink-0 rounded px-2 py-1 font-headline text-lg font-light uppercase tracking-wider underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-white"
        aria-haspopup="dialog"
        @click="about?.open()"
      >
        About
      </button>
    </header>
    <AboutDialog ref="about" />

    <!-- Each panel scrolls on its own on desktop. They're `relative` so absolutely positioned descendants (the
         cards' sr-only text) are clipped by the panel instead of stretching the whole page. -->
    <main class="grid flex-1 lg:min-h-0 lg:grid-cols-[45fr_55fr]">
      <!-- Map + filters -->
      <section
        class="relative space-y-6 border-wfp-gray bg-[#f7f6f2] px-4 py-5 sm:px-6 lg:overflow-y-auto lg:overscroll-contain lg:border-r-2"
        aria-label="Filters"
      >
        <div>
          <div class="mb-3 flex min-h-8 items-center justify-between gap-2">
            <h2 class="font-headline text-xl font-bold uppercase tracking-wide text-wfp-purple">
              {{ selectedTile ? selectedTile.state_name : 'All states' }}
            </h2>
            <button
              v-if="selectedTile"
              type="button"
              class="rounded bg-wfp-purple px-3 py-1 text-sm text-white hover:bg-wfp-purple/90"
              @click="selectedState = null"
            >
              Show all states ✕
            </button>
            <p v-else class="text-sm text-neutral-500">Click a state to filter</p>
          </div>
          <TileMap :states="STATE_TILES" :selected="selectedState" @select="selectState" />
          <MapLegend class="mt-4" />
        </div>

        <CategoryToggles v-model="enabledCategories" :counts="categoryCounts" />

        <StatusToggles v-model="enabledStatuses" :counts="statusCounts" />

        <p class="text-xs text-neutral-500">
          Data from
          <a :href="SOURCE_URL" class="underline" target="_blank" rel="noopener">workingfamilies.org</a>,
          updated {{ scrapedDate }}. Unofficial results from state and county election offices, updated
          {{ resultsTime }}.
        </p>
      </section>

      <!-- Candidate list -->
      <section class="relative px-4 pb-8 sm:px-6 lg:overflow-y-auto lg:overscroll-contain" aria-label="Endorsements">
        <div class="sticky top-0 z-20 -mx-4 bg-white px-4 pt-5 pb-3 sm:-mx-6 sm:px-6">
          <label class="sr-only" for="search">Search endorsements</label>
          <input
            id="search"
            v-model="search"
            type="search"
            placeholder="Search name, office, district…"
            class="w-full rounded border-2 border-wfp-gray px-3 py-2 outline-none focus:border-wfp-purple"
          />
          <p class="mt-2 text-sm text-neutral-600" aria-live="polite">
            Showing <strong class="tabular-nums">{{ visible.length }}</strong>
            of {{ inScope.length }} endorsements{{ selectedTile ? ` in ${selectedTile.state_name}` : '' }}
          </p>
        </div>
        <CandidateList :candidates="visible" />
      </section>
    </main>
  </div>
</template>
