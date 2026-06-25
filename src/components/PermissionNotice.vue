<template>
  <div class="flex items-start gap-3 px-4 py-3 rounded-xl bg-amber-500/20 border border-amber-400/30 text-amber-200 backdrop-blur-sm">
    <span class="text-xl flex-shrink-0 mt-0.5">⚠️</span>
    <div class="flex-1 min-w-0">
      <p class="font-medium text-amber-100">Location access was denied</p>
      <p class="text-sm mt-0.5 opacity-80">
        We couldn't access your location. Showing weather for
        <strong>{{ fallbackCity }}</strong> instead.
        You can search for any city using the search bar above, or grant location permission in your browser settings.
      </p>
    </div>
    <button
      @click="$emit('dismiss')"
      class="flex-shrink-0 p-1 rounded-lg hover:bg-amber-400/20 transition-colors text-amber-300 hover:text-amber-100"
      title="Dismiss"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  fallbackCity: string
}>()

defineEmits<{
  (e: 'dismiss'): void
}>()
</script>