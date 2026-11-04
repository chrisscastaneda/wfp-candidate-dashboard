<script setup lang="ts">
import { computed } from 'vue'
import type { CandidateResult } from '../data/types'

const props = defineProps<{ result: CandidateResult }>()

const choices = computed(() => props.result.choices ?? [])
const updated = computed(() => {
  const raw = props.result.updated_at
  if (!raw) return null
  const when = new Date(raw)
  // Some feeds give free text ("November 2, 2026, 6:28 p.m."); show it as-is.
  return Number.isNaN(when.getTime())
    ? raw.replace(/\.$/, '')
    : when.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
})
</script>

<template>
  <div class="mt-2 border-t border-wfp-gray pt-2 text-sm lg:text-base">
    <p class="mb-1.5 text-xs text-neutral-600 lg:text-sm">{{ result.contest }}</p>
    <table class="w-full">
      <tbody>
        <tr v-for="c in choices" :key="c.name" :class="c.is_wfp ? 'font-semibold' : ''">
          <td class="py-0.5 pr-2">
            {{ c.name }}
            <span v-if="c.party" class="text-xs font-normal text-neutral-500 lg:text-sm">{{ c.party }}</span>
          </td>
          <td class="w-2/5 py-0.5 pr-2">
            <div class="h-2 rounded-full bg-wfp-gray" aria-hidden="true">
              <div
                class="h-2 rounded-full"
                :class="c.is_wfp ? 'bg-wfp-purple' : 'bg-neutral-400'"
                :style="{ width: `${Math.min(100, c.pct ?? 0)}%` }"
              />
            </div>
          </td>
          <td class="py-0.5 pr-2 text-right tabular-nums">{{ (c.pct ?? 0).toFixed(1) }}%</td>
          <td class="py-0.5 text-right tabular-nums text-neutral-600">{{ c.votes.toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
    <p class="mt-1.5 text-xs text-neutral-500 lg:text-sm">
      <span v-if="result.reporting?.text">{{ result.reporting.text }}. </span>
      <span v-if="updated">Updated {{ updated }}. </span>
      Unofficial results; races aren't called here.
    </p>
    <p v-if="result.source_url" class="mt-1 text-xs text-neutral-500 lg:text-sm">
      Source:
      <a
        :href="result.source_url"
        target="_blank"
        rel="noopener"
        class="text-wfp-purple underline underline-offset-2 hover:text-wfp-orange"
        >{{ result.source_name ?? 'official results' }}<span aria-hidden="true"> ↗</span
        ><span class="sr-only"> (opens in a new tab)</span></a
      >
    </p>
  </div>
</template>
