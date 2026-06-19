<script setup lang="ts">
  import WeatherDashboard from '@/components/WeatherDashboard.vue'
  import { mockWeatherData } from '@/data/mockWeather'
  import { CONDITION_GRADIENTS } from '@/types/weather'
  import { computed } from 'vue'

  const gradientClass = computed(() => {
    return CONDITION_GRADIENTS[mockWeatherData.current.conditionCode]
  })
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br transition-all duration-1000"
    :class="gradientClass"
  >
    <!-- Subtle background pattern overlay -->
    <div
      class="fixed inset-0 opacity-10 pointer-events-none"
      style="
        background-image: radial-gradient(circle at 20% 50%, white 1px, transparent 1px),
          radial-gradient(circle at 80% 20%, white 1px, transparent 1px),
          radial-gradient(circle at 50% 80%, white 1px, transparent 1px);
        background-size: 60px 60px, 80px 80px, 40px 40px;
      "
    />

    <!-- App content -->
    <div class="relative z-10">
      <WeatherDashboard :weather="mockWeatherData" />
    </div>
  </div>
</template>