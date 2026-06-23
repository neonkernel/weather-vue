<template>
  <div
    class="
      flex flex-col items-center gap-2 p-4 rounded-2xl
      bg-white/10 backdrop-blur-sm border border-white/10
      hover:bg-white/15 transition-colors duration-200
      min-w-[100px]
    "
  >
    <p class="text-white/60 text-xs font-medium uppercase tracking-wide text-center">
      {{ day.dateFormatted }}
    </p>
    <span class="text-3xl" :title="day.weatherLabel" aria-hidden="true">{{ day.weatherEmoji }}</span>
    <p class="text-white/70 text-xs text-center">{{ day.weatherLabel }}</p>
    <div class="flex gap-2 items-baseline mt-1">
      <span class="text-white font-bold text-sm">{{ day.tempMax }}°</span>
      <span class="text-white/40 text-xs">{{ day.tempMin }}°</span>
    </div>
    <div v-if="day.precipitationSum > 0" class="flex items-center gap-1 text-blue-300">
      <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fill-rule="evenodd" d="M10 2a1 1 0 00-.832.445l-7 10A1 1 0 003 14h4v4a1 1 0 002 0v-4h2v4a1 1 0 002 0v-4h4a1 1 0 00.832-1.555l-7-10A1 1 0 0010 2z" clip-rule="evenodd" />
      </svg>
      <span class="text-xs">{{ day.precipitationSum.toFixed(1) }}mm</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ForecastDay } from '../types/weather'

defineProps<{
  day: ForecastDay
}>()
</script>