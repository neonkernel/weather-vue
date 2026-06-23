<template>
  <div class="flex flex-col items-center justify-center gap-4 py-16">
    <!-- Animated SVG Spinner -->
    <div class="relative">
      <svg
        class="w-16 h-16 animate-spin"
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <!-- Background track -->
        <circle
          cx="32"
          cy="32"
          r="28"
          stroke="rgba(255,255,255,0.15)"
          stroke-width="6"
        />
        <!-- Spinning arc -->
        <path
          d="M32 4 A28 28 0 0 1 60 32"
          stroke="white"
          stroke-width="6"
          stroke-linecap="round"
        />
      </svg>

      <!-- Center icon -->
      <div class="absolute inset-0 flex items-center justify-center">
        <span class="text-2xl" aria-hidden="true">🌤️</span>
      </div>
    </div>

    <!-- Label -->
    <div class="text-center">
      <p class="text-white font-semibold text-lg">{{ title }}</p>
      <p v-if="subtitle" class="text-white/60 text-sm mt-1">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string;
  subtitle?: string;
}

withDefaults(defineProps<Props>(), {
  title: 'Fetching weather...',
  subtitle: 'This will just take a moment',
});
</script>