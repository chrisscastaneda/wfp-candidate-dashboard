<script setup lang="ts">
import { computed } from 'vue'
import { CATEGORIES, CATEGORY_ORDER } from '../data/categories'
import type { Candidate } from '../data/types'
import CandidateCard from './CandidateCard.vue'

const props = defineProps<{ candidates: Candidate[] }>()

const LABELS = new Map(CATEGORIES.map((c) => [c.category, c.label]))

/** State (A–Z) → category (ballot order) → candidates (source order). */
const groups = computed(() => {
  const byState = new Map<string, Candidate[]>()
  for (const c of props.candidates) {
    if (!byState.has(c.state)) byState.set(c.state, [])
    byState.get(c.state)!.push(c)
  }
  return [...byState.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([state, rows]) => {
      const byCategory = new Map<string, Candidate[]>()
      for (const c of [...rows].sort(
        (a, b) => CATEGORY_ORDER.get(a.office_category)! - CATEGORY_ORDER.get(b.office_category)!,
      )) {
        const label = LABELS.get(c.office_category)!
        if (!byCategory.has(label)) byCategory.set(label, [])
        byCategory.get(label)!.push(c)
      }
      return { state, count: rows.length, categories: [...byCategory.entries()] }
    })
})
</script>

<template>
  <div class="space-y-8">
    <section v-for="group in groups" :key="group.state">
      <h2
        class="mb-3 flex items-baseline justify-between border-b-2 border-wfp-purple py-1.5 font-headline text-2xl font-bold uppercase tracking-wide text-wfp-purple lg:text-3xl"
      >
        {{ group.state }}
        <span class="font-sans text-sm font-normal normal-case tracking-normal text-neutral-500 lg:text-base">
          {{ group.count }}
        </span>
      </h2>
      <div v-for="[label, rows] in group.categories" :key="label" class="mb-4">
        <h3 class="mb-1.5 font-headline text-lg font-light uppercase tracking-wider text-neutral-700 lg:text-xl">
          {{ label }}
        </h3>
        <ul class="space-y-1.5">
          <CandidateCard v-for="c in rows" :key="c.id" :candidate="c" />
        </ul>
      </div>
    </section>
    <p v-if="!groups.length" class="py-16 text-center text-neutral-500">
      No endorsements match these filters.
    </p>
  </div>
</template>
