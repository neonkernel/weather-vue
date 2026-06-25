<template>
  <Transition name="slide-down">
    <div
      v-if="visible"
      class="flex items-start gap-3 px-4 py-3 rounded-xl border bg-amber-500/10 border-amber-500/30 text-amber-200 text-sm"
    >
      <span class="text-lg flex-shrink-0 mt-0.5">⚠️</span>
      <div class="flex-1 min-w-0">
        <p class="font-medium text-amber-100">Location access denied</p>
        <p class="text-amber-200/80 text-xs mt-0.5">
          We couldn't access your location. Showing weather for
          <strong class="text-amber-100">{{ fallbackCity }}</strong> instead.
          You can search for any city using the search bar above.
        </p>
      </div>
      <button
        @click="dismiss"
        class="flex-shrink-0 text-amber-300 hover:text-amber-100 transition-colors p-0.5 rounded"
        aria-label="Dismiss notice"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
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

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>