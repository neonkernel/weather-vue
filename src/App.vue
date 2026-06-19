<template>
  <div class="app-wrapper">
    <!-- Background gradient layer -->
    <div class="background-gradient" aria-hidden="true" />

    <!-- Decorative background orbs -->
    <div class="bg-orb bg-orb--1" aria-hidden="true" />
    <div class="bg-orb bg-orb--2" aria-hidden="true" />

    <!-- Main content -->
    <main class="app-content">
      <WeatherDashboard :weather="weatherData" />
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <p class="text-white/30 text-xs text-center py-4">
        Weather Dashboard &mdash; Built with Vue 3 + TypeScript
      </p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import WeatherDashboard from '@/components/WeatherDashboard.vue'
import { mockWeatherData } from '@/data/mockWeather'
import type { WeatherData } from '@/types/weather'

// In Phase 1 we use static mock data.
// Phase 2 will replace this with an API call.
const weatherData: WeatherData = mockWeatherData
</script>

<style scoped>
.app-wrapper {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.background-gradient {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #0d1b2a 0%, #1e3a5f 40%, #2d6a9f 80%, #56b4e9 100%);
  z-index: -2;
}

.bg-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  z-index: -1;
  pointer-events: none;
}

.bg-orb--1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(86, 180, 233, 0.25) 0%, transparent 70%);
  top: -200px;
  right: -200px;
}

.bg-orb--2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(45, 106, 159, 0.3) 0%, transparent 70%);
  bottom: -150px;
  left: -150px;
}

.app-content {
  flex: 1;
  position: relative;
  z-index: 1;
}

.app-footer {
  position: relative;
  z-index: 1;
}
</style>