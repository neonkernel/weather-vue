<template>
  <div class="space-y-4">
    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="h-48 animate-pulse rounded-2xl bg-white/10" />
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div v-for="i in 4" :key="i" class="h-24 animate-pulse rounded-xl bg-white/10" />
      </div>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-7">
        <div v-for="i in 7" :key="i" class="h-32 animate-pulse rounded-xl bg-white/10" />
      </div>
    </div>

    <!-- Weather data -->
    <template v-else-if="weatherData">
      <CurrentWeather :weather="weatherData.current" :timezone="weatherData.timezone" />

      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Humidity"
          :value="`${weatherData.current.relative_humidity_2m}%`"
          icon="💧"
        />
        <StatCard
          label="Feels Like"
          :value="`${Math.round(weatherData.current.apparent_temperature)}°C`"
          icon="🌡️"
        />
        <StatCard
          label="Wind"
          :value="`${Math.round(weatherData.current.wind_speed_10m)} km/h`"
          icon="💨"
        />
        <StatCard
          label="Precipitation"
          :value="`${weatherData.current.precipitation} mm`"
          icon="🌧️"
        />
      </div>

      <ForecastStrip
        v-if="weatherData.daily"
        :daily="weatherData.daily"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import type { WeatherData } from '../services/weatherService'
import CurrentWeather from './CurrentWeather.vue'
import StatCard from './StatCard.vue'
import ForecastStrip from './ForecastStrip.vue'

defineProps<{
  weatherData: WeatherData | null
  loading: boolean
  error: string | null
}>()
</script>