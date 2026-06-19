<template>
  <div class="glass-card current-weather">
    <!-- Top row: Location + condition -->
    <div class="current-weather__top">
      <div class="current-weather__location">
        <span class="location-pin" aria-hidden="true">📍</span>
        <div>
          <h2 class="city-name">{{ props.current.city }}</h2>
          <p class="country-name">{{ props.current.country }} &bull; {{ formattedDate }}</p>
        </div>
      </div>
      <div class="current-weather__condition">
        <span
          class="condition-icon"
          role="img"
          :aria-label="props.current.condition"
        >
          {{ props.current.icon }}
        </span>
        <p class="condition-text">{{ props.current.condition }}</p>
      </div>
    </div>

    <!-- Temperature display -->
    <div class="current-weather__temp-row">
      <div class="temp-wrapper">
        <span class="temp-display" :aria-label="`${props.current.temperature} degrees Celsius`">
          {{ props.current.temperature }}°
        </span>
        <span class="temp-unit">C</span>
      </div>
      <div class="feels-like">
        <span class="feels-like__label">Feels like</span>
        <span class="feels-like__value">{{ props.current.feelsLike }}°C</span>
      </div>
    </div>

    <!-- Divider -->
    <div class="divider" aria-hidden="true" />

    <!-- Stats grid -->
    <div class="current-weather__stats" role="list" aria-label="Weather statistics">
      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">💧</span>
        <span class="weather-stat-value">{{ props.current.humidity }}%</span>
        <span class="weather-stat-label">Humidity</span>
      </div>

      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">💨</span>
        <span class="weather-stat-value">{{ props.current.windSpeed }} km/h</span>
        <span class="weather-stat-label">Wind ({{ props.current.windDirection }})</span>
      </div>

      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">👁️</span>
        <span class="weather-stat-value">{{ props.current.visibility }} km</span>
        <span class="weather-stat-label">Visibility</span>
      </div>

      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">☀️</span>
        <span class="weather-stat-value">{{ props.current.uvIndex }}</span>
        <span class="weather-stat-label">UV Index</span>
      </div>

      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">🌅</span>
        <span class="weather-stat-value">{{ props.current.sunrise }}</span>
        <span class="weather-stat-label">Sunrise</span>
      </div>

      <div class="weather-stat" role="listitem">
        <span class="weather-stat-icon" aria-hidden="true">🌇</span>
        <span class="weather-stat-value">{{ props.current.sunset }}</span>
        <span class="weather-stat-label">Sunset</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WeatherCurrent } from '@/types/weather'

const props = defineProps<{
  current: WeatherCurrent
}>()

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
})
</script>

<style scoped>
.current-weather {
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.current-weather__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.current-weather__location {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.location-pin {
  font-size: 1.25rem;
  margin-top: 0.1rem;
}

.city-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
  line-height: 1.2;
}

.country-name {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.55);
  margin: 0.2rem 0 0;
}

.current-weather__condition {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.condition-icon {
  font-size: 3rem;
  line-height: 1;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3));
}

.condition-text {
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  margin: 0;
  white-space: nowrap;
}

.current-weather__temp-row {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
}

.temp-wrapper {
  display: flex;
  align-items: flex-start;
  line-height: 1;
}

.temp-display {
  font-size: clamp(4rem, 12vw, 7rem);
  font-weight: 800;
  color: white;
  letter-spacing: -0.04em;
  line-height: 1;
}

.temp-unit {
  font-size: 2rem;
  font-weight: 300;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 0.75rem;
  margin-left: 0.1rem;
}

.feels-like {
  display: flex;
  flex-direction: column;
  padding-bottom: 0.5rem;
}

.feels-like__label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.feels-like__value {
  font-size: 1.25rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
}

.current-weather__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

@media (min-width: 480px) {
  .current-weather__stats {
    grid-template-columns: repeat(6, 1fr);
  }
}

@media (min-width: 640px) {
  .current-weather {
    padding: 2rem;
  }
}
</style>