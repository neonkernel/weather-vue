<script setup lang="ts">
import type { WeatherCurrent } from '@/types/weather'
import { CONDITION_ICONS } from '@/types/weather'
import { computed } from 'vue'

interface Props {
  current: WeatherCurrent
}

const props = defineProps<Props>()

const conditionIcon = computed(() => CONDITION_ICONS[props.current.conditionCode] ?? '🌡️')

// Derive temperature color hint
const tempColorClass = computed(() => {
  const t = props.current.temperature
  if (t >= 30) return 'text-orange-200'
  if (t >= 20) return 'text-yellow-100'
  if (t >= 10) return 'text-sky-100'
  return 'text-blue-200'
})
</script>

<template>
  <div class="glass-card p-6 sm:p-8">
    <!-- Location row -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-white text-2xl sm:text-3xl font-bold text-shadow-md leading-tight">
          {{ current.city }}
        </h2>
        <p class="text-white/70 text-sm font-medium mt-0.5">
          {{ current.country }}
        </p>
      </div>
      <!-- Condition icon (large) -->
      <div class="text-5xl sm:text-6xl select-none" role="img" :aria-label="current.condition">
        {{ conditionIcon }}
      </div>
    </div>

    <!-- Temperature block -->
    <div class="flex items-end gap-4 mb-6">
      <div>
        <div class="temp-display text-7xl sm:text-8xl" :class="tempColorClass">
          {{ current.temperature }}<span class="text-4xl sm:text-5xl align-top mt-2 inline-block text-white/80">°C</span>
        </div>
        <p class="text-white/70 text-sm mt-1">
          Feels like {{ current.feelsLike }}°C &nbsp;·&nbsp; {{ current.condition }}
        </p>
      </div>
    </div>

    <!-- Stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <!-- Humidity -->
      <div class="stat-pill">
        <span class="text-lg" role="img" aria-label="Humidity">💧</span>
        <div>
          <p class="text-white/60 text-xs leading-none mb-0.5">Humidity</p>
          <p class="font-semibold">{{ current.humidity }}%</p>
        </div>
      </div>

      <!-- Wind -->
      <div class="stat-pill">
        <span class="text-lg" role="img" aria-label="Wind">💨</span>
        <div>
          <p class="text-white/60 text-xs leading-none mb-0.5">Wind</p>
          <p class="font-semibold">{{ current.windSpeed }} <span class="text-white/70 font-normal">km/h {{ current.windDirection }}</span></p>
        </div>
      </div>

      <!-- UV Index -->
      <div class="stat-pill">
        <span class="text-lg" role="img" aria-label="UV Index">☀️</span>
        <div>
          <p class="text-white/60 text-xs leading-none mb-0.5">UV Index</p>
          <p class="font-semibold">{{ current.uvIndex }}</p>
        </div>
      </div>

      <!-- Visibility -->
      <div class="stat-pill">
        <span class="text-lg" role="img" aria-label="Visibility">👁️</span>
        <div>
          <p class="text-white/60 text-xs leading-none mb-0.5">Visibility</p>
          <p class="font-semibold">{{ current.visibility }} <span class="text-white/70 font-normal">km</span></p>
        </div>
      </div>
    </div>

    <!-- Sunrise / Sunset -->
    <div class="flex items-center gap-6 mt-5 pt-5 border-t border-white/15">
      <div class="flex items-center gap-2 text-white/80">
        <span class="text-xl" role="img" aria-label="Sunrise">🌅</span>
        <div>
          <p class="text-white/50 text-xs">Sunrise</p>
          <p class="text-sm font-semibold">{{ current.sunrise }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2 text-white/80">
        <span class="text-xl" role="img" aria-label="Sunset">🌇</span>
        <div>
          <p class="text-white/50 text-xs">Sunset</p>
          <p class="text-sm font-semibold">{{ current.sunset }}</p>
        </div>
      </div>
      <div class="ml-auto flex items-center gap-2 text-white/80">
        <span class="text-xl" role="img" aria-label="Pressure">🌡️</span>
        <div>
          <p class="text-white/50 text-xs">Pressure</p>
          <p class="text-sm font-semibold">{{ current.pressure }} <span class="text-white/60 font-normal text-xs">hPa</span></p>
        </div>
      </div>
    </div>
  </div>
</template>