<template>
  <div class="glass-card p-6 md:p-8 animate-slide-up">
    <!-- Location -->
    <div class="flex items-start justify-between flex-wrap gap-4 mb-6">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="text-white/60 text-sm">📍</span>
          <h2 class="text-white font-semibold text-xl text-shadow">
            {{ current.city }},
            <span class="text-white/70 font-normal">{{ current.country }}</span>
          </h2>
        </div>
        <p class="text-white/50 text-sm ml-6">{{ formattedDate }}</p>
      </div>

      <!-- UV Index badge -->
      <div class="flex flex-col items-end gap-1">
        <span
          class="px-3 py-1 rounded-full text-xs font-semibold"
          :class="uvBadgeClass"
        >
          UV {{ current.uvIndex }} · {{ uvLabel }}
        </span>
        <span class="text-white/40 text-xs">Pressure: {{ current.pressure }} hPa</span>
      </div>
    </div>

    <!-- Main temperature display -->
    <div class="flex items-center gap-6 md:gap-10 mb-6">
      <!-- Icon -->
      <div class="text-7xl md:text-8xl select-none" role="img" :aria-label="current.condition">
        {{ current.icon }}
      </div>

      <!-- Temp + condition -->
      <div>
        <div class="temp-display">
          {{ current.temperature }}<span class="text-4xl md:text-5xl font-thin text-white/70">{{ unitSymbol }}</span>
        </div>
        <p class="text-white/80 text-lg font-light mt-1 text-shadow-sm">{{ current.condition }}</p>
        <p class="text-white/50 text-sm mt-0.5">
          Feels like {{ current.feelsLike }}{{ unitSymbol }}
        </p>
      </div>
    </div>

    <!-- Divider -->
    <hr class="glass-divider border-t mb-5" />

    <!-- Weather stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <!-- Humidity -->
      <div class="stat-pill flex-col items-start gap-1 py-3">
        <span class="text-white/50 text-xs uppercase tracking-wider">💧 Humidity</span>
        <span class="text-white font-semibold text-base">{{ current.humidity }}%</span>
      </div>

      <!-- Wind -->
      <div class="stat-pill flex-col items-start gap-1 py-3">
        <span class="text-white/50 text-xs uppercase tracking-wider">💨 Wind</span>
        <span class="text-white font-semibold text-base">
          {{ current.windSpeed }} {{ speedUnit }}
          <span class="text-white/60 text-sm font-normal">{{ current.windDirection }}</span>
        </span>
      </div>

      <!-- Visibility -->
      <div class="stat-pill flex-col items-start gap-1 py-3">
        <span class="text-white/50 text-xs uppercase tracking-wider">👁️ Visibility</span>
        <span class="text-white font-semibold text-base">{{ current.visibility }} km</span>
      </div>

      <!-- Sunrise / Sunset -->
      <div class="stat-pill flex-col items-start gap-1 py-3">
        <span class="text-white/50 text-xs uppercase tracking-wider">🌅 Sun</span>
        <span class="text-white font-semibold text-sm leading-snug">
          ↑ {{ current.sunrise }}<br />
          <span class="text-white/75">↓ {{ current.sunset }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherCurrent } from '@/types/weather'

const props = defineProps<{
  current: WeatherCurrent
  units: 'metric' | 'imperial'
}>()

const unitSymbol = computed(() => (props.units === 'metric' ? '°C' : '°F'))
const speedUnit = computed(() => (props.units === 'metric' ? 'km/h' : 'mph'))

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

const uvLabel = computed(() => {
  const uv = props.current.uvIndex
  if (uv <= 2) return 'Low'
  if (uv <= 5) return 'Moderate'
  if (uv <= 7) return 'High'
  if (uv <= 10) return 'Very High'
  return 'Extreme'
})

const uvBadgeClass = computed(() => {
  const uv = props.current.uvIndex
  if (uv <= 2) return 'bg-green-500/30 text-green-200 border border-green-400/30'
  if (uv <= 5) return 'bg-yellow-500/30 text-yellow-200 border border-yellow-400/30'
  if (uv <= 7) return 'bg-orange-500/30 text-orange-200 border border-orange-400/30'
  if (uv <= 10) return 'bg-red-500/30 text-red-200 border border-red-400/30'
  return 'bg-purple-500/30 text-purple-200 border border-purple-400/30'
})
</script>