<template>
  <div
    v-if="visible"
    class="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-4 py-3 text-sm shadow-sm"
    role="alert"
  >
    <span class="text-xl leading-none mt-0.5" aria-hidden="true">📍</span>
    <div class="flex-1">
      <p class="font-semibold">Location access denied</p>
      <p class="text-amber-700 mt-0.5">
        We couldn't access your location. Showing weather for
        <strong>{{ fallbackCity }}</strong> instead. You can search for any city above.
      </p>
    </div>
    <button
      @click="visible = false"
      class="text-amber-500 hover:text-amber-700 transition-colors ml-2 leading-none text-lg font-bold"
      aria-label="Dismiss notice"
    >
      ×
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    fallbackCity?: string
  }>(),
  {
    fallbackCity: 'New York',
  }
)

const visible = ref(true)
</script>