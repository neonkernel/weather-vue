<template>
  <div class="flex flex-col items-center justify-center py-16 gap-4" role="status" aria-label="Loading weather data">
    <div class="relative">
      <!-- Outer ring -->
      <svg
        class="w-16 h-16 animate-spin text-white/30"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="3"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>

      <!-- Center icon -->
      <div class="absolute inset-0 flex items-center justify-center">
        <span class="text-2xl animate-pulse" aria-hidden="true">🌤️</span>
      </div>
    </div>

    <div class="text-center">
      <p class="text-white/80 font-medium text-lg">{{ message }}</p>
      <p v-if="subMessage" class="text-white/50 text-sm mt-1">{{ subMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message?: string
    subMessage?: string
  }>(),
  {
    message: 'Fetching weather data...',
    subMessage: 'This may take a moment',
  }
)
</script>