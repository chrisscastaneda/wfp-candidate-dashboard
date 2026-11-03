<script setup lang="ts">
import { ref } from 'vue'

const dialog = ref<HTMLDialogElement | null>(null)

defineExpose({ open: () => dialog.value?.showModal() })

/** Clicks on the backdrop land on the <dialog> itself, outside its content box. */
function closeOnBackdrop(event: MouseEvent) {
  if (event.target === dialog.value) dialog.value?.close()
}
</script>

<template>
  <!-- Native modal: traps focus, closes on Esc, and never navigates or reloads the page. On phones it fills most of
       the window to cut down on scrolling. From sm up its middle sits a third of the way down the window, and the
       height cap keeps its top edge on screen. -->
  <dialog
    ref="dialog"
    aria-labelledby="about-title"
    class="mx-auto mt-[5dvh] w-[min(40rem,calc(100%-2rem))] rounded sm:mt-[33dvh] sm:-translate-y-1/2 p-0 shadow-xl backdrop:bg-black/50"
    @click="closeOnBackdrop"
  >
    <div class="max-h-[90dvh] overflow-y-auto sm:max-h-[60dvh] px-5 py-4 sm:px-6">
      <div class="mb-3 flex items-start justify-between gap-4">
        <h2 id="about-title" class="font-headline text-2xl font-bold uppercase tracking-wide text-wfp-purple">
          About
        </h2>
        <button
          type="button"
          class="-mr-1 rounded px-2 text-2xl leading-none text-neutral-500 hover:text-neutral-900"
          aria-label="Close"
          @click="dialog?.close()"
        >
          ×
        </button>
      </div>
      <div class="space-y-3 text-neutral-700">
        <p>
          This is the personal project of Chris Castañeda-Barajas, a curious citizen, political data nerd, and progressive supporter of the Working Families Party. This project is in no way officially affiliated with the Working Families Party.
        </p>
        <p>
          Endorsed candidates are drawn from the Working Families Party’s public candidate list. Results come directly from official state and county election websites and are updated periodically as votes are counted. I’m still working to bring scrapers online for every jurisdiction, so races marked “Results not tracked yet” will fill in as more sources come online.
        </p>
        <p>
          Every effort has been made to ensure that the data reflected on this site is accurate. If you notice an
          inaccuracy or find some other issue with the site, please feel free to log an issue here:
          <a
            href="https://github.com/chrisscastaneda/wfp-candidate-dashboard/issues"
            target="_blank"
            rel="noopener"
            class="break-words text-wfp-purple underline underline-offset-2 hover:text-wfp-orange"
            >github.com/chrisscastaneda/wfp-candidate-dashboard/issues</a
          >.
        </p>
        <p class="text-2xl">✊</p>
      </div>
    </div>
  </dialog>
</template>
