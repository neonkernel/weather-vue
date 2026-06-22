<script setup lang="ts">
import type { WeatherData } from '@/types/weather'
import CurrentWeather from '@/components/CurrentWeather.vue'
import ForecastStrip from '@/components/ForecastStrip.vue'

const props = defineProps<{
  data: WeatherData
}>()
</script>

<template>
  <div class="weather-dashboard max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8 animate-fade-in">
    <!-- Dashboard Header -->
    <header class="mb-8 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-3xl" aria-hidden="true">🌤️</span>
        <h1 class="text-xl font-semibold text-white/90 text-shadow-sm tracking-wide">
          Weather Dashboard
        </h1>
      </div>
      <span class="text-sm text-white/60 font-medium">
        Phase 1 — Static UI
      </span>
    </header>

    <!-- Current Weather Section -->
    <section
      aria-label="Current weather conditions"
      class="mb-6 animate-slide-up"
      style="animation-delay: 0.05s"
    >
      <CurrentWeather :current="props.data.current" />
    </section>

    <!-- 7-Day Forecast Section -->
    <section
      aria-label="7-day forecast"
      class="animate-slide-up"
      style="animation-delay: 0.15s"
    >
      <h2 class="text-sm font-semibold uppercase tracking-widest text-white/60 mb-3 pl-1">
        7-Day Forecast
      </h2>
      <ForecastStrip :days="props.data.forecast" />
    </section>

    <!-- Footer -->
    <footer class="mt-8 text-center text-xs text-white/40">
      <p>Data shown is placeholder · Phase 2 will connect a live weather API</p>
    </footer>
  </div>
</template>