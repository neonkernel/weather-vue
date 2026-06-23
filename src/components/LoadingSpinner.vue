<template>
  <div class="flex flex-col items-center justify-center gap-4 py-16" aria-label="Loading weather data" role="status">
    <!-- Animated SVG Spinner -->
    <div class="relative w-16 h-16">
      <svg
        class="w-16 h-16 animate-spin text-white/30"
        fill="none"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
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
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>

      <!-- Pulsing center dot -->
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="w-3 h-3 bg-white/60 rounded-full animate-pulse" />
      </div>
    </div>

    <!-- Label -->
    <div class="text-center">
      <p class="text-white/80 font-medium text-sm sm:text-base">{{ message }}</p>
      <p v-if="subMessage" class="text-white/50 text-xs mt-1">{{ subMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message?: string;
    subMessage?: string;
  }>(),
  {
    message: 'Fetching weather data…',
    subMessage: 'This should only take a moment.',
  }
);
</script>