<template>
  <main class="min-h-screen w-full px-4 py-8 sm:px-6 lg:px-8 animate-fade-in">
    <div class="mx-auto max-w-4xl space-y-6">
      <!-- Header -->
      <header class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-3xl" aria-hidden="true">🌤️</span>
          <h1 class="text-xl font-semibold tracking-tight text-white/90">
            Weather Dashboard
          </h1>
        </div>
        <p class="text-sm text-white/50">
          Updated {{ formattedTime }}
        </p>
      </header>

      <!-- Current Weather -->
      <section aria-label="Current weather conditions">
        <CurrentWeather :data="weatherData.current" />
      </section>

      <!-- 7-Day Forecast -->
      <section aria-label="7-day weather forecast">
        <h2 class="mb-3 text-sm font-medium uppercase tracking-widest text-white/50">
          7-Day Forecast
        </h2>
        <ForecastStrip :forecast="weatherData.forecast" />
      </section>

      <!-- Footer -->
      <footer class="pt-2 text-center text-xs text-white/30">
        Weather data is for demonstration purposes only.
      </footer>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CurrentWeather from '@/components/CurrentWeather.vue'
import ForecastStrip from '@/components/ForecastStrip.vue'
import { mockWeatherData } from '@/data/mockWeather'

const weatherData = mockWeatherData

const formattedTime = computed(() => {
  const date = new Date(weatherData.current.updatedAt)
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
})
</script>