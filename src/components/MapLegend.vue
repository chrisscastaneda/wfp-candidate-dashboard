<script setup lang="ts">
import Tile from './Tile.vue'

const ITEMS = [
  { label: 'U.S. House', notches: { topLeft: true } },
  { label: 'U.S. Senate', notches: { topRight: true } },
  { label: 'State House', notches: { bottomLeft: true } },
  { label: 'State Senate', notches: { bottomRight: true } },
]
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-neutral-700">
    <div v-for="item in ITEMS" :key="item.label" class="flex items-center gap-1.5">
      <div class="pointer-events-none w-6" aria-hidden="true">
        <Tile label="" :notches="item.notches" :notch-size="0.5" tabindex="-1" />
      </div>
      {{ item.label }}
    </div>
    <div class="flex items-center gap-1.5">
      <div class="pointer-events-none w-6" aria-hidden="true">
        <Tile label="" tone="muted" tabindex="-1" />
      </div>
      No endorsements
    </div>
  </div>
</template>
