<template>
  <div class="app-wrapper min-h-screen w-full">
    <WeatherDashboard />
  </div>
</template>

<script setup lang="ts">
import WeatherDashboard from '@/components/WeatherDashboard.vue'
</script>

<style scoped>
.app-wrapper {
  background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
}
</style>