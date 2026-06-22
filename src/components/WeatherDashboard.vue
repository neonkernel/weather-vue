<script setup lang="ts">
import { ref } from 'vue'
import CurrentWeather from '@/components/CurrentWeather.vue'
import ForecastStrip from '@/components/ForecastStrip.vue'
import { mockWeatherData } from '@/data/mockWeather'
import type { WeatherData } from '@/types/weather'

const weatherData = ref<WeatherData>(mockWeatherData)
</script>

<template>
  <main class="min-h-dvh w-full px-4 py-6 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-4xl space-y-6">

      <!-- Header -->
      <header class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-2xl">🌤️</span>
          <h1 class="text-xl font-semibold text-white tracking-tight">WeatherBoard</h1>
        </div>
        <span class="text-sm text-muted">
          {{ weatherData.current.lastUpdated }}
        </span>
      </header>

      <!-- Current Weather Section -->
      <section aria-label="Current weather conditions">
        <CurrentWeather :current="weatherData.current" />
      </section>

      <!-- 7-Day Forecast Section -->
      <section aria-label="7-day forecast">
        <div class="mb-3 flex items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-widest text-muted">
            📅 7-Day Forecast
          </span>
        </div>
        <ForecastStrip :forecast="weatherData.forecast" />
      </section>

      <!-- Footer -->
      <footer class="text-center">
        <p class="text-xs text-muted">
          Coordinates: {{ weatherData.lat }}°N, {{ Math.abs(weatherData.lon) }}°W
          · {{ weatherData.timezone }}
        </p>
      </footer>

    </div>
  </main>
</template>