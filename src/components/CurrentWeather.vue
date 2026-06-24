<template>
  <div class="rounded-2xl bg-white/5 border border-white/10 p-6 backdrop-blur-sm">
    <!-- City & Time -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <h2 class="text-2xl font-bold text-white">{{ cityName }}</h2>
        <p class="text-slate-400 text-sm mt-1">{{ formattedTime }}</p>
      </div>
      <div class="text-right">
        <p class="text-5xl font-thin text-white">{{ Math.round(weather.temperature) }}°C</p>
        <p class="text-slate-400 text-sm mt-1">Feels like {{ Math.round(weather.feelsLike) }}°C</p>
      </div>
    </div>

    <!-- Weather description -->
    <div class="flex items-center gap-2 mb-6">
      <span class="text-3xl">{{ weatherEmoji }}</span>
      <span class="text-lg text-slate-200">{{ weatherDescription }}</span>
    </div>

    <!-- Stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label="Humidity" :value="`${weather.humidity}%`" icon="💧" />
      <StatCard label="Wind" :value="`${Math.round(weather.windSpeed)} km/h`" icon="💨" />
      <StatCard label="Pressure" :value="`${Math.round(weather.pressure)} hPa`" icon="📊" />
      <StatCard label="UV Index" :value="weather.uvIndex?.toString() ?? 'N/A'" icon="☀️" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatCard from './StatCard.vue'
import type { WeatherData } from '../types/weather'
import { getWeatherDescription, getWeatherEmoji } from '../utils/weatherCodeMap'

const props = defineProps<{
  weather: WeatherData
  cityName: string
}>()

const formattedTime = computed(() => {
  try {
    return new Date(props.weather.time).toLocaleString('en-US', {
      weekday: 'long',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
  } catch {
    return props.weather.time
  }
})

const weatherDescription = computed(() => getWeatherDescription(props.weather.weatherCode))
const weatherEmoji = computed(() => getWeatherEmoji(props.weather.weatherCode))
</script>