<template>
  <div class="text-white">
    <!-- Location -->
    <div class="flex items-center gap-2 mb-6">
      <svg class="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <div>
        <h2 class="text-2xl font-bold leading-none">{{ city }}</h2>
        <p class="text-white/60 text-sm mt-0.5">{{ country }}</p>
      </div>
      <span class="ml-auto text-xs text-white/40">Updated {{ lastUpdatedFormatted }}</span>
    </div>

    <!-- Main temperature display -->
    <div class="flex items-start justify-between mb-8">
      <div>
        <div class="flex items-start gap-2">
          <span class="text-8xl font-thin leading-none tracking-tighter">
            {{ weather.temperature }}
          </span>
          <div class="mt-4">
            <span class="text-3xl font-light text-white/80">°C</span>
          </div>
        </div>
        <div class="mt-2 flex flex-col gap-1">
          <p class="text-xl text-white/80 font-medium">{{ weather.weatherEmoji }} {{ weather.weatherLabel }}</p>
          <p class="text-white/50 text-sm">Feels like {{ weather.feelsLike }}°C</p>
        </div>
      </div>

      <!-- Day/Night indicator -->
      <div class="flex flex-col items-center gap-1 mt-2">
        <span class="text-5xl">{{ weather.isDay ? '☀️' : '🌙' }}</span>
        <span class="text-xs text-white/40">{{ weather.isDay ? 'Daytime' : 'Nighttime' }}</span>
      </div>
    </div>

    <!-- Stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard
        icon="💧"
        label="Humidity"
        :value="`${weather.humidity}%`"
      />
      <StatCard
        icon="💨"
        label="Wind"
        :value="`${weather.windSpeed} km/h`"
      />
      <StatCard
        icon="🌡️"
        label="UV Index"
        :value="uvLabel"
      />
      <StatCard
        icon="👁️"
        label="Visibility"
        :value="`${weather.visibility} km`"
      />
    </div>

    <!-- Precipitation -->
    <div v-if="weather.precipitation > 0" class="mt-3">
      <StatCard
        icon="🌧️"
        label="Precipitation"
        :value="`${weather.precipitation} mm`"
        class="w-full sm:w-1/2"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherCurrent } from '../types/weather'
import StatCard from './StatCard.vue'
import { formatTime } from '../utils/unitConverters'

const props = defineProps<{
  weather: WeatherCurrent
  city: string
  country: string
  lastUpdated: string
}>()

const lastUpdatedFormatted = computed(() => formatTime(props.lastUpdated))

const uvLabel = computed(() => {
  const uv = props.weather.uvIndex
  if (uv <= 2) return `${uv} Low`
  if (uv <= 5) return `${uv} Moderate`
  if (uv <= 7) return `${uv} High`
  if (uv <= 10) return `${uv} Very High`
  return `${uv} Extreme`
})
</script>