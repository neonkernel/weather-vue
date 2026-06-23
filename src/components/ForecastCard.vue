<template>
  <div
    class="
      flex flex-col items-center gap-2
      bg-white/5 hover:bg-white/10 transition-colors duration-200
      rounded-2xl px-3 py-4 border border-white/5
      min-w-[90px] flex-shrink-0
    "
  >
    <!-- Date label -->
    <p class="text-slate-400 text-xs font-medium uppercase tracking-wider text-center leading-tight">
      {{ day.dateFormatted }}
    </p>

    <!-- Weather emoji -->
    <div class="text-3xl leading-none" :title="day.weatherLabel" aria-label="day.weatherLabel">
      {{ day.weatherEmoji }}
    </div>

    <!-- Temp range -->
    <div class="flex flex-col items-center leading-tight">
      <span class="text-white font-semibold text-base">{{ day.tempMax }}°</span>
      <span class="text-slate-500 text-sm">{{ day.tempMin }}°</span>
    </div>

    <!-- Rain probability -->
    <div
      v-if="day.precipitationProbability > 0"
      class="flex items-center gap-0.5 text-sky-400 text-xs font-medium"
      :title="`${day.precipitationProbability}% chance of rain`"
    >
      <span aria-hidden="true">💧</span>
      {{ day.precipitationProbability }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ForecastDay } from '../types/weather';

defineProps<{
  day: ForecastDay;
}>();
</script>