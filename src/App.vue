<script setup lang="ts">
import WeatherDashboard from '@/components/WeatherDashboard.vue'
import { mockWeatherData } from '@/data/mockWeather'
import { CONDITION_GRADIENTS } from '@/types/weather'
import { computed } from 'vue'

// Derive the background gradient from the current weather condition
const bgGradient = computed(() => {
  const code = mockWeatherData.current.conditionCode
  return CONDITION_GRADIENTS[code] ?? 'from-sky-500 via-sky-600 to-blue-700'
})
</script>

<template>
  <div
    class="min-h-screen w-full bg-gradient-to-br transition-all duration-700"
    :class="bgGradient"
  >
    <!-- Subtle background pattern overlay -->
    <div
      class="fixed inset-0 pointer-events-none"
      style="
        background-image: radial-gradient(circle at 20% 80%, rgba(255,255,255,0.06) 0%, transparent 50%),
                          radial-gradient(circle at 80% 20%, rgba(255,255,255,0.08) 0%, transparent 50%),
                          radial-gradient(circle at 50% 50%, rgba(0,0,0,0.05) 0%, transparent 70%);
      "
    />

    <!-- Main content -->
    <div class="relative z-10 min-h-screen">
      <WeatherDashboard :weather="mockWeatherData" />
    </div>
  </div>
</template>