<script setup lang="ts">
// Root component — provides global layout shell.
// All weather UI lives inside WeatherDashboard.
import WeatherDashboard from '@/components/WeatherDashboard.vue'
</script>

<template>
  <div class="min-h-dvh w-full">
    <!-- Global background gradient is applied via body in main.css -->
    <WeatherDashboard />
  </div>
</template>