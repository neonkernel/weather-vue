<template>
  <div class="app-wrapper min-h-screen">
    <!-- Background gradient overlay for depth -->
    <div class="fixed inset-0 pointer-events-none" aria-hidden="true">
      <div
        class="absolute inset-0 bg-gradient-to-br from-weather-primary via-weather-secondary to-sky-400 opacity-95"
      />
      <!-- Decorative blurred orbs for glassmorphism background depth -->
      <div
        class="absolute top-[-10%] right-[-5%] w-96 h-96 rounded-full bg-blue-400 opacity-20 blur-3xl"
      />
      <div
        class="absolute bottom-[-15%] left-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-600 opacity-20 blur-3xl"
      />
      <div
        class="absolute top-[40%] left-[30%] w-64 h-64 rounded-full bg-sky-300 opacity-10 blur-2xl"
      />
    </div>

    <!-- Main content -->
    <div class="relative z-10 min-h-screen flex flex-col">
      <WeatherDashboard :weather="weatherData" />
    </div>
  </div>
</template>

<script setup lang="ts">
import WeatherDashboard from '@/components/WeatherDashboard.vue'
import { mockWeatherData } from '@/data/mockWeather'
import type { WeatherData } from '@/types/weather'

// In Phase 1, we use hardcoded mock data. Future phases will fetch from an API.
const weatherData: WeatherData = mockWeatherData
</script>

<style scoped>
.app-wrapper {
  background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 40%, #4a90d9 70%, #87ceeb 100%);
  background-attachment: fixed;
}
</style>