<template>
  <div>
    <h2 class="text-white/70 text-sm font-semibold uppercase tracking-widest mb-4">
      7-Day Forecast
    </h2>
    <div class="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
      <ForecastCard
        v-for="day in forecast"
        :key="day.date"
        :day="day"
        class="flex-shrink-0"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DailyForecastData } from '../services/weatherService';
import ForecastCard from './ForecastCard.vue';

interface Props {
  forecast: DailyForecastData[];
}

defineProps<Props>();
</script>

<style scoped>
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>