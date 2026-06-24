<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    enter-from-class="opacity-0 -translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition-all duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 -translate-y-2"
  >
    <div
      v-if="visible"
      class="flex items-start gap-3 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm"
    >
      <span class="text-lg flex-shrink-0 mt-0.5">⚠️</span>
      <div class="flex-1 min-w-0">
        <p class="font-medium text-amber-100">Location access denied</p>
        <p class="text-amber-300/80 text-xs mt-0.5">
          Unable to detect your location. Showing weather for
          <span class="font-semibold text-amber-200">{{ fallbackCity }}</span> instead.
          You can search for any city using the search bar.
        </p>
      </div>
      <button
        @click="dismiss"
        class="flex-shrink-0 p-1 rounded-lg hover:bg-amber-500/20 transition-colors text-amber-400 hover:text-amber-200"
        aria-label="Dismiss notice"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  fallbackCity: string
}>()

const visible = ref(true)

function dismiss() {
  visible.value = false
}
</script>