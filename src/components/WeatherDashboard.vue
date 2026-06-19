<template>
  <div class="dashboard">
    <div class="dashboard__container">
      <!-- Header -->
      <header class="dashboard__header">
        <div class="flex items-center gap-2">
          <span class="text-2xl" aria-hidden="true">🌤️</span>
          <h1 class="text-white/80 text-lg font-semibold tracking-wide">Weather Dashboard</h1>
        </div>
        <div class="flex items-center gap-2 text-white/50 text-sm">
          <span>🕐</span>
          <time :datetime="props.weather.current.lastUpdated">
            Updated {{ formattedUpdateTime }}
          </time>
        </div>
      </header>

      <!-- Current Weather Section -->
      <section aria-label="Current weather conditions" class="dashboard__section">
        <CurrentWeather :current="props.weather.current" />
      </section>

      <!-- 7-Day Forecast Section -->
      <section aria-label="7-day weather forecast" class="dashboard__section">
        <h2 class="section-title">7-Day Forecast</h2>
        <ForecastStrip :forecast="props.weather.forecast" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import CurrentWeather from '@/components/CurrentWeather.vue'
import ForecastStrip from '@/components/ForecastStrip.vue'
import type { WeatherData } from '@/types/weather'

const props = defineProps<{
  weather: WeatherData
}>()

const formattedUpdateTime = computed(() => {
  try {
    const date = new Date(props.weather.current.lastUpdated)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })
  } catch {
    return 'just now'
  }
})
</script>

<style scoped>
.dashboard {
  width: 100%;
  padding: 1rem;
}

.dashboard__container {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.dashboard__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.25rem;
}

.dashboard__section {
  animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (min-width: 640px) {
  .dashboard {
    padding: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .dashboard {
    padding: 2rem;
  }
}
</style>