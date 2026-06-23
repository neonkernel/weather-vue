<template>
  <div class="text-white">
    <!-- City & Date -->
    <div class="mb-6">
      <h1 class="text-3xl md:text-4xl font-bold tracking-tight">{{ cityName }}</h1>
      <p class="text-white/70 mt-1 text-sm">{{ formattedDate }}</p>
    </div>

    <!-- Main Temperature Block -->
    <div class="flex items-center gap-6 mb-8">
      <div class="text-7xl md:text-8xl font-thin leading-none">
        {{ weather.temperature }}°
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-4xl" aria-hidden="true">{{ weatherInfo.emoji }}</span>
        <span class="text-lg font-medium text-white/90">{{ weatherInfo.label }}</span>
        <span class="text-sm text-white/60">Feels like {{ weather.apparentTemperature }}°C</span>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard icon="💧" label="Humidity" :value="`${weather.humidity}%`" />
      <StatCard icon="💨" label="Wind" :value="`${weather.windSpeed} km/h`" />
      <StatCard icon="🌧️" label="Precipitation" :value="`${weather.precipitation} mm`" />
      <StatCard icon="🧭" label="Wind Dir." :value="windDirectionLabel" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { CurrentWeatherData } from '../services/weatherService';
import { getWeatherInfo } from '../utils/weatherCodeMap';
import StatCard from './StatCard.vue';

interface Props {
  weather: CurrentWeatherData;
  cityName: string;
}

const props = defineProps<Props>();

const weatherInfo = computed(() => getWeatherInfo(props.weather.weatherCode));

const formattedDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

const windDirectionLabel = computed(() => {
  const deg = props.weather.windDirection;
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
});
</script>