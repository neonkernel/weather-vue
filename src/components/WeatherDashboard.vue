<template>
  <main class="weather-dashboard w-full max-w-4xl mx-auto px-4 py-8 md:py-12 animate-fade-in">
    <!-- Header -->
    <header class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-white text-xl font-semibold tracking-wide text-shadow">
          🌤️ Weather Dashboard
        </h1>
        <p class="text-white/50 text-xs mt-0.5">
          Last updated: {{ formattedLastUpdated }}
        </p>
      </div>
      <div class="stat-pill text-xs">
        <span class="w-2 h-2 rounded-full bg-green-400 inline-block animate-pulse"></span>
        Live Preview
      </div>
    </header>

    <!-- Current Weather Section -->
    <section class="mb-6" aria-label="Current weather">
      <CurrentWeather :current="weather.current" :units="weather.units" />
    </section>

    <!-- 7-Day Forecast Section -->
    <section aria-label="7-day forecast">
      <div class="flex items-center justify-between mb-3 px-1">
        <h2 class="text-white/70 text-sm font-medium uppercase tracking-widest text-shadow-sm">
          📅 7-Day Forecast
        </h2>
        <span class="text-white/40 text-xs">{{ weather.units === 'metric' ? '°C' : '°F' }}</span>
      </div>
      <ForecastStrip :forecast="weather.forecast" :units="weather.units" />
    </section>

    <!-- Footer -->
    <footer class="mt-8 text-center">
      <p class="text-white/30 text-xs">
        Data provided by {{ weather.provider }} · Phase 1 Static UI
      </p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CurrentWeather from '@/components/CurrentWeather.vue'
import ForecastStrip from '@/components/ForecastStrip.vue'
import type { WeatherData } from '@/types/weather'

const props = defineProps<{
  weather: WeatherData
}>()

const formattedLastUpdated = computed(() => {
  try {
    const date = new Date(props.weather.current.lastUpdated)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })
  } catch {
    return props.weather.current.lastUpdated
  }
})
</script>