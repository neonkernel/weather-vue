<script setup lang="ts">
import type { WeatherCurrent } from '@/types/weather'

defineProps<{
  current: WeatherCurrent
}>()

/**
 * Returns a Tailwind color class based on UV index severity.
 */
function uvColor(uvIndex: number): string {
  if (uvIndex <= 2) return 'text-green-400'
  if (uvIndex <= 5) return 'text-yellow-400'
  if (uvIndex <= 7) return 'text-orange-400'
  if (uvIndex <= 10) return 'text-red-400'
  return 'text-purple-400'
}

/**
 * Returns a human-readable UV index label.
 */
function uvLabel(uvIndex: number): string {
  if (uvIndex <= 2) return 'Low'
  if (uvIndex <= 5) return 'Moderate'
  if (uvIndex <= 7) return 'High'
  if (uvIndex <= 10) return 'Very High'
  return 'Extreme'
}
</script>

<template>
  <div class="glass-card p-6 animate-fade-in">

    <!-- Location & Condition -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">

      <!-- Left: Temperature & Location -->
      <div class="flex flex-col gap-1">
        <div class="flex items-baseline gap-1">
          <h2 class="text-5xl sm:text-7xl font-bold text-white leading-none tracking-tighter">
            {{ current.temperature }}°
          </h2>
          <span class="text-2xl font-light text-secondary mt-2">C</span>
        </div>

        <p class="text-lg text-secondary mt-1">
          Feels like <span class="font-medium text-white">{{ current.feelsLike }}°C</span>
        </p>

        <div class="flex items-center gap-2 mt-2">
          <span class="text-3xl" role="img" :aria-label="current.condition">
            {{ current.icon }}
          </span>
          <div>
            <p class="text-xl font-semibold text-white">{{ current.condition }}</p>
            <p class="text-sm text-secondary">
              {{ current.city }}, {{ current.country }}
            </p>
          </div>
        </div>
      </div>

      <!-- Right: Sun Times -->
      <div class="flex gap-4 sm:flex-col sm:items-end sm:gap-2">
        <div class="flex items-center gap-2">
          <span class="text-yellow-400 text-lg">🌅</span>
          <div>
            <p class="text-xs text-muted uppercase tracking-wide">Sunrise</p>
            <p class="text-sm font-semibold text-white">{{ current.sunrise }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-orange-400 text-lg">🌇</span>
          <div>
            <p class="text-xs text-muted uppercase tracking-wide">Sunset</p>
            <p class="text-sm font-semibold text-white">{{ current.sunset }}</p>
          </div>
        </div>
      </div>

    </div>

    <!-- Divider -->
    <hr class="my-5 border-white/10" />

    <!-- Stats Grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">

      <!-- Humidity -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="Humidity">💧</span>
        <span class="text-xs text-muted uppercase tracking-wide">Humidity</span>
        <span class="text-sm font-bold text-white">{{ current.humidity }}%</span>
      </div>

      <!-- Wind -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="Wind">💨</span>
        <span class="text-xs text-muted uppercase tracking-wide">Wind</span>
        <span class="text-sm font-bold text-white">
          {{ current.windSpeed }} <span class="font-normal text-secondary text-xs">km/h</span>
        </span>
        <span class="text-xs text-secondary">{{ current.windDirection }}</span>
      </div>

      <!-- Visibility -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="Visibility">👁️</span>
        <span class="text-xs text-muted uppercase tracking-wide">Visibility</span>
        <span class="text-sm font-bold text-white">
          {{ current.visibility }} <span class="font-normal text-secondary text-xs">km</span>
        </span>
      </div>

      <!-- UV Index -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="UV Index">☀️</span>
        <span class="text-xs text-muted uppercase tracking-wide">UV Index</span>
        <span class="text-sm font-bold text-white">{{ current.uvIndex }}</span>
        <span class="text-xs font-medium" :class="uvColor(current.uvIndex)">
          {{ uvLabel(current.uvIndex) }}
        </span>
      </div>

      <!-- Pressure -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="Pressure">🔵</span>
        <span class="text-xs text-muted uppercase tracking-wide">Pressure</span>
        <span class="text-sm font-bold text-white">
          {{ current.pressure }} <span class="font-normal text-secondary text-xs">hPa</span>
        </span>
      </div>

      <!-- Cloud / Condition Badge -->
      <div class="stat-badge">
        <span class="text-xl" role="img" aria-label="Condition">🌡️</span>
        <span class="text-xs text-muted uppercase tracking-wide">Condition</span>
        <span class="text-xs font-semibold text-white text-center leading-tight">
          {{ current.condition }}
        </span>
      </div>

    </div>

  </div>
</template>