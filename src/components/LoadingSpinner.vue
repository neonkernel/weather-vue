<template>
  <div
    class="flex flex-col items-center justify-center gap-4 py-16"
    role="status"
    aria-live="polite"
    aria-label="Loading weather data"
  >
    <!-- Animated rings -->
    <div class="relative w-20 h-20">
      <svg
        class="absolute inset-0 w-full h-full animate-spin"
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="40"
          cy="40"
          r="34"
          stroke="currentColor"
          stroke-width="6"
          stroke-linecap="round"
          stroke-dasharray="160 54"
          class="text-sky-400"
        />
      </svg>
      <svg
        class="absolute inset-0 w-full h-full animate-spin"
        style="animation-direction: reverse; animation-duration: 1.5s"
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="40"
          cy="40"
          r="22"
          stroke="currentColor"
          stroke-width="4"
          stroke-linecap="round"
          stroke-dasharray="80 60"
          class="text-sky-300/60"
        />
      </svg>
      <!-- Cloud + sun in centre -->
      <div class="absolute inset-0 flex items-center justify-center text-2xl select-none" aria-hidden="true">
        🌤️
      </div>
    </div>

    <p class="text-slate-300 text-sm font-medium tracking-wide animate-pulse">
      {{ message }}
    </p>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message?: string;
  }>(),
  {
    message: 'Fetching weather data…',
  }
);
</script>