<script setup lang="ts">
  import type { WeatherData } from '@/types/weather'
  import CurrentWeather from '@/components/CurrentWeather.vue'
  import ForecastStrip from '@/components/ForecastStrip.vue'

  interface Props {
    weather: WeatherData
  }

  const props = defineProps<Props>()
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="flex items-center justify-between px-6 py-4 md:px-10">
      <div class="flex items-center gap-2">
        <span class="text-2xl">🌤️</span>
        <span class="text-white/90 font-semibold text-lg tracking-wide">WeatherDash</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-white/60 text-sm">
          Updated {{ new Date(props.weather.current.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
        </span>
        <button
          class="glass-card px-4 py-2 text-white/80 text-sm font-medium hover:text-white hover:bg-white/20 transition-all duration-200"
          aria-label="Refresh weather data"
        >
          ↻ Refresh
        </button>
      </div>
    </header>

    <!-- Main content -->
    <main class="flex-1 flex flex-col gap-6 px-4 py-6 md:px-10 md:py-8 max-w-5xl mx-auto w-full">
      <!-- Current weather section -->
      <section aria-label="Current weather conditions">
        <CurrentWeather :current="props.weather.current" />
      </section>

      <!-- Forecast section -->
      <section aria-label="7-day weather forecast">
        <h2 class="text-white/70 text-sm font-semibold uppercase tracking-widest mb-3 px-1">
          7-Day Forecast
        </h2>
        <ForecastStrip :forecast="props.weather.forecast" />
      </section>
    </main>

    <!-- Footer -->
    <footer class="text-center py-4 text-white/40 text-xs">
      Weather Dashboard — Phase 1 Static UI
    </footer>
  </div>
</template>