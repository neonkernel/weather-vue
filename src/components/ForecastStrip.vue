<template>
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-7">
    <ForecastCard
      v-for="(day, index) in days"
      :key="day.date"
      :date="day.date"
      :weather-code="day.weatherCode"
      :temp-max="day.tempMax"
      :temp-min="day.tempMin"
      :precipitation="day.precipitation"
      :is-today="index === 0"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ForecastCard from './ForecastCard.vue'

const props = defineProps<{
  daily: {
    time: string[]
    weather_code: number[]
    temperature_2m_max: number[]
    temperature_2m_min: number[]
    precipitation_sum: number[]
  }
}>()

const days = computed(() =>
  props.daily.time.map((date, i) => ({
    date,
    weatherCode: props.daily.weather_code[i],
    tempMax: props.daily.temperature_2m_max[i],
    tempMin: props.daily.temperature_2m_min[i],
    precipitation: props.daily.precipitation_sum[i],
  }))
)
</script>