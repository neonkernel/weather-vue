<script setup lang="ts">
import type { WeatherCurrent } from '@/types/weather'

const props = defineProps<{
  current: WeatherCurrent
}>()

/** Format the lastUpdated ISO string into a readable local time */
function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/** Compute a UV risk label */
function uvLabel(index: number): string {
  if (index <= 2) return 'Low'
  if (index <= 5) return 'Moderate'
  if (index <= 7) return 'High'
  if (index <= 10) return 'Very High'
  return 'Extreme'
}
</script>

<template>
  <div class="glass-card p-6 sm:p-8">
    <!-- Location & timestamp row -->
    <div class="flex flex-wrap items-start justify-between gap-2 mb-6">
      <div>
        <h2 class="text-3xl sm:text-4xl font-bold text-white text-shadow leading-tight">
          {{ props.current.city }}
        </h2>
        <p class="text-white/70 text-sm mt-1 font-medium">
          {{ props.current.country }} ·
          Updated {{ formatTime(props.current.lastUpdated) }}
        </p>
      </div>
      <!-- Sunrise / Sunset -->
      <div class="flex gap-4 text-sm text-white/70">
        <span class="flex items-center gap-1">
          <span aria-hidden="true">🌅</span>
          <span>{{ props.current.sunrise }}</span>
        </span>
        <span class="flex items-center gap-1">
          <span aria-hidden="true">🌇</span>
          <span>{{ props.current.sunset }}</span>
        </span>
      </div>
    </div>

    <!-- Temperature & condition row -->
    <div class="flex flex-wrap items-center gap-6 mb-8">
      <!-- Big temperature -->
      <div class="flex items-end gap-3">
        <span
          class="weather-icon text-7xl sm:text-8xl leading-none select-none"
          :title="props.current.condition"
          aria-hidden="true"
        >
          {{ props.current.conditionIcon }}
        </span>
        <div>
          <p class="text-7xl sm:text-8xl font-thin text-white text-shadow leading-none tabular-nums">
            {{ props.current.tempC }}<span class="text-4xl align-top mt-3 inline-block">°C</span>
          </p>
          <p class="text-white/70 text-sm mt-1">
            Feels like {{ props.current.feelsLikeC }}°C
          </p>
        </div>
      </div>
      <!-- Condition label -->
      <div class="ml-auto">
        <span class="text-2xl sm:text-3xl font-light text-white/90 text-shadow">
          {{ props.current.condition }}
        </span>
      </div>
    </div>

    <!-- Stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <!-- Humidity -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">💧</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">Humidity</p>
          <p class="text-white font-semibold text-sm leading-snug">{{ props.current.humidity }}%</p>
        </div>
      </div>

      <!-- Wind -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">💨</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">Wind</p>
          <p class="text-white font-semibold text-sm leading-snug">
            {{ props.current.windKph }} km/h {{ props.current.windDir }}
          </p>
        </div>
      </div>

      <!-- Pressure -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">🌡️</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">Pressure</p>
          <p class="text-white font-semibold text-sm leading-snug">{{ props.current.pressureHpa }} hPa</p>
        </div>
      </div>

      <!-- Visibility -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">👁️</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">Visibility</p>
          <p class="text-white font-semibold text-sm leading-snug">{{ props.current.visibilityKm }} km</p>
        </div>
      </div>

      <!-- UV Index -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">☀️</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">UV Index</p>
          <p class="text-white font-semibold text-sm leading-snug">
            {{ props.current.uvIndex }} · {{ uvLabel(props.current.uvIndex) }}
          </p>
        </div>
      </div>

      <!-- Dew Point -->
      <div class="stat-chip flex-col sm:flex-row">
        <span class="text-lg" aria-hidden="true">🌿</span>
        <div class="text-center sm:text-left">
          <p class="text-white/60 text-xs leading-none">Dew Point</p>
          <p class="text-white font-semibold text-sm leading-snug">{{ props.current.dewPointC }}°C</p>
        </div>
      </div>
    </div>
  </div>
</template>