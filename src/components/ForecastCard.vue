<template>
  <div class="flex flex-col items-center gap-1.5 p-2 rounded-xl hover:bg-white/5 transition-colors duration-150">
    <p class="text-xs text-slate-400 font-medium">{{ dayLabel }}</p>
    <span class="text-2xl">{{ weatherEmoji }}</span>
    <p class="text-sm font-semibold text-white">{{ Math.round(forecast.tempMax) }}°</p>
    <p class="text-xs text-slate-500">{{ Math.round(forecast.tempMin) }}°</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ForecastData } from '../types/weather'
import { getWeatherEmoji } from '../utils/weatherCodeMap'

const props = defineProps<{
  forecast: ForecastData
}>()

const dayLabel = computed(() => {
  try {
    const date = new Date(props.forecast.time)
    return date.toLocaleDateString('en-US', { weekday: 'short' })
  } catch {
    return props.forecast.time
  }
})

const weatherEmoji = computed(() => getWeatherEmoji(props.forecast.weatherCode))
</script>