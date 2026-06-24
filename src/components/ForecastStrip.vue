<template>
  <div class="rounded-2xl bg-white/5 border border-white/10 p-5 backdrop-blur-sm">
    <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">7-Day Forecast</h3>
    <div class="grid grid-cols-7 gap-2">
      <ForecastCard
        v-for="day in forecast"
        :key="day.time"
        :forecast="day"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import ForecastCard from './ForecastCard.vue'
import type { ForecastData } from '../types/weather'

defineProps<{
  forecast: ForecastData[]
}>()
</script>