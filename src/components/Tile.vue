<script setup lang="ts">
/**
 * A square map tile: a centered label, a border, and up to four corner notches.
 * It knows nothing about states or candidates; StateTile maps data onto it.
 */
export interface TileNotches {
  topLeft?: boolean
  topRight?: boolean
  bottomLeft?: boolean
  bottomRight?: boolean
}

/** highlight: has data · muted: no data · active: currently selected */
export type TileTone = 'highlight' | 'muted' | 'active'

const props = withDefaults(
  defineProps<{
    label: string
    notches?: TileNotches
    tone?: TileTone
    disabled?: boolean
    ariaLabel?: string
    pressed?: boolean
    /** Notch side length as a fraction of the tile's side. */
    notchSize?: number
  }>(),
  { notches: () => ({}), tone: 'highlight', disabled: false, pressed: undefined, notchSize: 0.3 },
)

defineEmits<{ click: [event: MouseEvent] }>()

const CORNERS = ['topLeft', 'topRight', 'bottomLeft', 'bottomRight'] as const
</script>

<template>
  <button
    type="button"
    class="tile"
    :class="`tile--${props.tone}`"
    :disabled="props.disabled"
    :aria-label="props.ariaLabel ?? props.label"
    :aria-pressed="props.pressed"
    :title="props.ariaLabel ?? props.label"
    :style="{ '--tile-notch-size': `${props.notchSize * 100}%` }"
    @click="$emit('click', $event)"
  >
    <span
      v-for="corner in CORNERS"
      v-show="props.notches[corner]"
      :key="corner"
      class="tile__notch"
      :class="`tile__notch--${corner}`"
      aria-hidden="true"
    />
    <span class="tile__label">{{ props.label }}</span>
  </button>
</template>

<style scoped>
.tile {
  /* --tile-ink drives the border, label and notches together. */
  --tile-ink: var(--color-wfp-orange);
  --tile-fill: #fde4df;
  --tile-border: 2px;

  container-type: inline-size;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 3px;
  background: var(--tile-fill);
  /* Inset shadow instead of border so notches can sit flush with the outer corner. */
  box-shadow: inset 0 0 0 var(--tile-border) var(--tile-ink);
  color: var(--tile-ink);
  cursor: pointer;
  transition:
    transform 120ms ease,
    background-color 120ms ease;
}
.tile:hover:not(:disabled) {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--tile-fill) 80%, var(--tile-ink));
}
.tile:focus-visible {
  outline: 3px solid var(--color-wfp-purple);
  outline-offset: 2px;
}
.tile:disabled {
  cursor: default;
}

.tile--muted {
  --tile-ink: #b3ae9f;
  --tile-fill: var(--color-wfp-gray);
}
.tile--active {
  --tile-ink: var(--color-wfp-purple);
  --tile-fill: var(--color-wfp-marigold);
}

.tile__label {
  position: relative;
  font-family: var(--font-headline);
  font-weight: 700;
  font-size: 40cqw;
  line-height: 1;
  letter-spacing: 0.02em;
}

/* Right triangles (30% of the tile's side by default), flush with each corner. */
.tile__notch {
  position: absolute;
  width: var(--tile-notch-size);
  height: var(--tile-notch-size);
  background: var(--tile-ink);
}
.tile__notch--topLeft {
  top: 0;
  left: 0;
  clip-path: polygon(0 0, 100% 0, 0 100%);
}
.tile__notch--topRight {
  top: 0;
  right: 0;
  clip-path: polygon(0 0, 100% 0, 100% 100%);
}
.tile__notch--bottomLeft {
  bottom: 0;
  left: 0;
  clip-path: polygon(0 0, 0 100%, 100% 100%);
}
.tile__notch--bottomRight {
  bottom: 0;
  right: 0;
  clip-path: polygon(100% 0, 100% 100%, 0 100%);
}
</style>
