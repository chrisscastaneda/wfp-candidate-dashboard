<script setup lang="ts">
import { CATEGORIES } from '../data/categories'
import type { OfficeCategory } from '../data/types'

const enabled = defineModel<Set<OfficeCategory>>({ required: true })
defineProps<{ counts: Map<OfficeCategory, number> }>()

function toggle(category: OfficeCategory) {
  const next = new Set(enabled.value)
  if (next.has(category)) next.delete(category)
  else next.add(category)
  enabled.value = next
}

function setAll(on: boolean) {
  enabled.value = new Set(on ? CATEGORIES.map((c) => c.category) : [])
}
</script>

<template>
  <fieldset>
    <div class="mb-2 flex items-baseline justify-between gap-2">
      <legend class="font-headline text-xl font-bold uppercase tracking-wide text-wfp-purple">
        Office type
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
        v-for="c in CATEGORIES"
        :key="c.category"
        class="flex cursor-pointer items-center gap-2 rounded border-2 px-2.5 py-1.5 text-sm transition-colors select-none"
        :class="
          enabled.has(c.category)
            ? 'border-wfp-orange bg-[#fde4df] text-neutral-900'
            : 'border-wfp-gray bg-white text-neutral-500'
        "
      >
        <input
          type="checkbox"
          class="size-4 accent-wfp-orange"
          :checked="enabled.has(c.category)"
          @change="toggle(c.category)"
        />
        <span class="flex-1">{{ c.label }}</span>
        <span class="tabular-nums text-neutral-500">{{ counts.get(c.category) ?? 0 }}</span>
      </label>
    </div>
  </fieldset>
</template>
