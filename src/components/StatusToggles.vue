<script setup lang="ts">
import { STATUSES } from '../data/results'
import type { DisplayStatus } from '../data/types'

const enabled = defineModel<Set<DisplayStatus>>({ required: true })
defineProps<{ counts: Map<DisplayStatus, number> }>()

function toggle(status: DisplayStatus) {
  const next = new Set(enabled.value)
  if (next.has(status)) next.delete(status)
  else next.add(status)
  enabled.value = next
}

function setAll(on: boolean) {
  enabled.value = new Set(on ? STATUSES.map((s) => s.status) : [])
}
</script>

<template>
  <fieldset>
    <div class="mb-2 flex items-baseline justify-between gap-2">
      <legend class="font-headline text-xl font-bold uppercase tracking-wide text-wfp-purple">
        Results
      </legend>
      <div class="flex gap-3 text-sm">
        <button type="button" class="text-wfp-purple underline-offset-2 hover:underline" @click="setAll(true)">
          All
        </button>
        <button type="button" class="text-wfp-purple underline-offset-2 hover:underline" @click="setAll(false)">
          None
        </button>
      </div>
    </div>
    <div class="grid grid-cols-1 gap-1.5 min-[420px]:grid-cols-2">
      <label
        v-for="s in STATUSES"
        :key="s.status"
        class="flex cursor-pointer items-center gap-2 rounded border-2 px-2.5 py-1.5 text-sm transition-colors select-none"
        :class="
          enabled.has(s.status)
            ? 'border-wfp-orange bg-[#fde4df] text-neutral-900'
            : 'border-wfp-gray bg-white text-neutral-500'
        "
      >
        <input
          type="checkbox"
          class="size-4 accent-wfp-orange"
          :checked="enabled.has(s.status)"
          @change="toggle(s.status)"
        />
        <span class="flex-1">{{ s.label }}</span>
        <span class="tabular-nums text-neutral-500">{{ counts.get(s.status) ?? 0 }}</span>
      </label>
    </div>
  </fieldset>
</template>
