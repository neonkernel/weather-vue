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
  <main class="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
    <!-- App header -->
    <header class="text-center mb-8 animate-fade-in">
      <p class="section-label mb-2">Weather Dashboard</p>
      <h1 class="text-white/90 text-lg font-medium text-shadow-sm">
        Your personal forecast at a glance
      </h1>
    </header>

    <!-- Current weather section -->
    <section class="mb-6 animate-slide-up" style="animation-delay: 0.1s">
      <CurrentWeather :current="props.weather.current" />
    </section>

    <!-- 7-day forecast section -->
    <section class="animate-slide-up" style="animation-delay: 0.2s">
      <div class="mb-3 px-1">
        <p class="section-label">7-Day Forecast</p>
      </div>
      <ForecastStrip :forecast="props.weather.forecast" />
    </section>

    <!-- Footer -->
    <footer class="mt-8 text-center animate-fade-in" style="animation-delay: 0.4s">
      <p class="text-white/40 text-xs">
        Last updated: {{ new Date(props.weather.current.lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
        &nbsp;·&nbsp;
        Data provided for demonstration purposes
      </p>
    </footer>
  </main>
</template>