<template>
  <div
    class="relative mb-6 flex items-start gap-3 p-4 rounded-xl bg-amber-500/20 border border-amber-400/30 backdrop-blur text-amber-100"
    role="alert"
  >
    <!-- Icon -->
    <span class="text-xl flex-shrink-0 mt-0.5">⚠️</span>

    <!-- Content -->
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium">Location access was denied</p>
      <p class="text-xs mt-0.5 text-amber-200">
        We couldn't detect your location.
        <span v-if="fallbackCity">
          Showing weather for <strong>{{ fallbackCity }}</strong> instead.
        </span>
        You can search for any city manually or try enabling location access in your browser settings.
      </p>
    </div>

    <!-- Dismiss Button -->
    <button
      type="button"
      class="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-amber-200 hover:text-white hover:bg-amber-400/30 transition focus:outline-none focus:ring-2 focus:ring-amber-400"
      aria-label="Dismiss notification"
      @click="$emit('dismiss')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  fallbackCity?: string
}>()

defineEmits<{
  dismiss: []
}>()
</script>