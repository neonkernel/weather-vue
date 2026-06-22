<template>
  <div class="glass-card p-6 sm:p-8 animate-slide-up">
    <div class="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
      <!-- Location & Condition -->
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="text-lg" aria-hidden="true">📍</span>
          <h2 class="text-2xl font-bold tracking-tight text-white">
            {{ data.city }},
            <span class="font-normal text-white/70">{{ data.country }}</span>
          </h2>
        </div>
        <p class="pl-7 text-sm text-white/60">{{ data.condition }}</p>
      </div>

      <!-- Temperature Block -->
      <div class="flex items-end gap-4">
        <div class="text-right">
          <div class="flex items-start justify-end">
            <span class="text-7xl font-extrabold leading-none tracking-tighter text-white">
              {{ data.temperature }}
            </span>
            <span class="mt-3 text-3xl font-light text-white/70">°C</span>
          </div>
          <p class="text-sm text-white/50">
            Feels like {{ data.feelsLike }}°C
          </p>
        </div>
        <span class="text-6xl leading-none" role="img" :aria-label="data.condition">
          {{ data.icon }}
        </span>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <!-- Humidity -->
      <div class="glass-card p-4 text-center">
        <div class="mb-1 text-2xl" aria-hidden="true">💧</div>
        <p class="stat-label">Humidity</p>
        <p class="stat-value">{{ data.humidity }}%</p>
      </div>

      <!-- Wind -->
      <div class="glass-card p-4 text-center">
        <div class="mb-1 text-2xl" aria-hidden="true">💨</div>
        <p class="stat-label">Wind</p>
        <p class="stat-value">{{ data.windSpeed }} km/h</p>
        <p class="text-xs text-white/40">{{ data.windDirection }}</p>
      </div>

      <!-- Visibility -->
      <div class="glass-card p-4 text-center">
        <div class="mb-1 text-2xl" aria-hidden="true">👁️</div>
        <p class="stat-label">Visibility</p>
        <p class="stat-value">{{ data.visibility }} km</p>
      </div>

      <!-- UV Index -->
      <div class="glass-card p-4 text-center">
        <div class="mb-1 text-2xl" aria-hidden="true">☀️</div>
        <p class="stat-label">UV Index</p>
        <p class="stat-value">{{ data.uvIndex }}</p>
        <p class="text-xs text-white/40">{{ uvLabel }}</p>
      </div>
    </div>

    <!-- Sunrise / Sunset -->
    <div class="mt-4 flex items-center justify-around rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <div class="flex items-center gap-2">
        <span class="text-xl" aria-hidden="true">🌅</span>
        <div>
          <p class="stat-label">Sunrise</p>
          <p class="text-sm font-semibold text-white">{{ data.sunrise }}</p>
        </div>
      </div>
      <div class="h-8 w-px bg-white/15" aria-hidden="true" />
      <div class="flex items-center gap-2">
        <span class="text-xl" aria-hidden="true">🌇</span>
        <div>
          <p class="stat-label">Sunset</p>
          <p class="text-sm font-semibold text-white">{{ data.sunset }}</p>
        </div>
      </div>
      <div class="h-8 w-px bg-white/15" aria-hidden="true" />
      <div class="flex items-center gap-2">
        <span class="text-xl" aria-hidden="true">🔵</span>
        <div>
          <p class="stat-label">Pressure</p>
          <p class="text-sm font-semibold text-white">{{ data.pressure }} hPa</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherCurrent } from '@/types/weather'

const props = defineProps<{
  data: WeatherCurrent
}>()

const uvLabel = computed(() => {
  const uv = props.data.uvIndex
  if (uv <= 2) return 'Low'
  if (uv <= 5) return 'Moderate'
  if (uv <= 7) return 'High'
  if (uv <= 10) return 'Very High'
  return 'Extreme'
})
</script>