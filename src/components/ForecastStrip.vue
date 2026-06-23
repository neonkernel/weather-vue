<template>
  <div class="w-full">
    <h3 class="text-slate-400 text-sm font-medium uppercase tracking-wider mb-3">
      7-Day Forecast
    </h3>
    <div
      class="
        flex gap-3 overflow-x-auto pb-2
        scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent
      "
      role="list"
      aria-label="7-day forecast"
    >
      <div
        v-for="day in forecast"
        :key="day.date"
        role="listitem"
      >
        <ForecastCard :day="day" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ForecastDay } from '../types/weather';
import ForecastCard from './ForecastCard.vue';

defineProps<{
  forecast: ForecastDay[];
}>();
</script>