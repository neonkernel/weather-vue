<template>
  <div>
    <h3 class="text-white/70 text-sm font-semibold uppercase tracking-wider mb-4">
      7-Day Forecast
    </h3>
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
import type { ForecastDay } from '../types/weather'
import ForecastCard from './ForecastCard.vue'

defineProps<{
  forecast: ForecastDay[]
}>()
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