<template>
  <div class="space-y-6">
    <!-- Current Weather -->
    <CurrentWeather :weather="weather" :city-name="cityName" />

    <!-- Forecast Strip -->
    <ForecastStrip v-if="forecast && forecast.length" :forecast="forecast" />
  </div>
</template>

<script setup lang="ts">
import CurrentWeather from './CurrentWeather.vue'
import ForecastStrip from './ForecastStrip.vue'
import type { WeatherData, ForecastData } from '../types/weather'

defineProps<{
  weather: WeatherData
  forecast: ForecastData[]
  cityName: string
}>()
</script>