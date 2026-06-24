<template>
  <div class="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-white/60">Current Weather</p>
        <div class="mt-1 flex items-end gap-2">
          <span class="text-6xl font-thin text-white">
            {{ Math.round(weather.temperature_2m) }}°
          </span>
          <span class="mb-2 text-2xl text-white/60">C</span>
        </div>
        <p class="mt-2 text-lg text-white/80">{{ weatherDescription }}</p>
      </div>
      <div class="text-7xl">{{ weatherEmoji }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getWeatherDescription, getWeatherEmoji } from '../utils/weatherCodeMap'

const props = defineProps<{
  weather: {
    temperature_2m: number
    weather_code: number
    is_day: number
    relative_humidity_2m: number
    apparent_temperature: number
    precipitation: number
    wind_speed_10m: number
    wind_direction_10m: number
  }
  timezone: string
}>()

const weatherDescription = computed(() =>
  getWeatherDescription(props.weather.weather_code)
)

const weatherEmoji = computed(() =>
  getWeatherEmoji(props.weather.weather_code, props.weather.is_day === 1)
)
</script>