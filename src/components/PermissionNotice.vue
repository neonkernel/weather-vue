<script setup lang="ts">
const props = defineProps<{
  fallbackCity: string
}>()

const emit = defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <div
    class="flex items-start gap-3 p-4 mb-5 bg-amber-900/30 border border-amber-700/50 rounded-xl text-amber-200"
    role="alert"
  >
    <!-- Icon -->
    <div class="flex-shrink-0 mt-0.5">
      <svg
        class="w-5 h-5 text-amber-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    </div>

    <!-- Message -->
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-amber-300 text-sm">Location access denied</p>
      <p class="text-sm mt-0.5 text-amber-200/80">
        We couldn't access your location. Showing weather for
        <strong class="text-amber-200">{{ fallbackCity }}</strong> instead.
        You can search for any city or enable location permissions in your browser settings.
      </p>
    </div>

    <!-- Dismiss button -->
    <button
      type="button"
      class="flex-shrink-0 p-1 rounded-lg hover:bg-amber-800/40 text-amber-400 hover:text-amber-200 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500"
      aria-label="Dismiss notice"
      @click="emit('dismiss')"
    >
      <svg
        class="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </div>
</template>