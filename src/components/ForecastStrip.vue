<template>
  <div class="w-full">
    <h3 class="text-white/70 text-sm font-medium uppercase tracking-wider mb-3">7-Day Forecast</h3>
    <div class="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <ForecastCard
        v-for="(day, index) in forecast"
        :key="day.date"
        :day="day"
        :is-today="index === 0"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import ForecastCard from './ForecastCard.vue';
import type { ForecastDay } from '../types/weather';

defineProps<{
  forecast: ForecastDay[];
}>();
</script>