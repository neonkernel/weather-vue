<script setup lang="ts">
import WeatherDashboard from '@/components/WeatherDashboard.vue'
import { mockWeatherData } from '@/data/mockWeather'
</script>

<template>
  <div class="app-wrapper min-h-dvh w-full">
    <!-- Global background gradient — full viewport -->
    <div
      class="fixed inset-0 -z-10 bg-gradient-to-br from-weather-primary via-weather-secondary to-weather-accent"
      aria-hidden="true"
    />

    <!-- Decorative blurred orbs for depth -->
    <div
      class="fixed -top-32 -right-32 w-96 h-96 rounded-full bg-weather-accent opacity-20 blur-3xl pointer-events-none -z-10"
      aria-hidden="true"
    />
    <div
      class="fixed -bottom-32 -left-32 w-80 h-80 rounded-full bg-weather-warm opacity-15 blur-3xl pointer-events-none -z-10"
      aria-hidden="true"
    />

    <!-- Main content -->
    <main class="relative z-0 min-h-dvh">
      <WeatherDashboard :data="mockWeatherData" />
    </main>
  </div>
</template>