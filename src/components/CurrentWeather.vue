<template>
  <div class="text-white">
    <!-- Location & date -->
    <div class="mb-4">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-white/60 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <h2 class="text-lg sm:text-xl font-semibold tracking-wide">{{ location.displayName }}</h2>
      </div>
      <p class="text-white/60 text-sm mt-1 ml-6">{{ currentDate }}</p>
    </div>

    <!-- Main temperature and condition -->
    <div class="flex items-center gap-4 mb-6">
      <div class="text-7xl sm:text-8xl leading-none select-none" aria-hidden="true">
        {{ weatherInfo.emoji }}
      </div>
      <div>
        <div class="text-6xl sm:text-7xl font-thin tracking-tighter leading-none">
          {{ weather.temperature }}<span class="text-4xl align-top mt-2 inline-block">°C</span>
        </div>
        <div class="text-white/80 text-lg mt-1 font-light">{{ weatherInfo.label }}</div>
        <div class="text-white/50 text-sm">Feels like {{ weather.feelsLike }}°C</div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard icon="💧" label="Humidity" :value="`${weather.humidity}%`" />
      <StatCard icon="💨" label="Wind" :value="`${weather.windSpeed} km/h`" />
      <StatCard icon="🌧️" label="Precipitation" :value="`${weather.precipitation} mm`" />
      <StatCard icon="🔆" label="UV Index" :value="uvLabel" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import StatCard from './StatCard.vue';
import { getWeatherInfo } from '../utils/weatherCodeMap';
import type { WeatherCurrent, GeoLocation } from '../types/weather';

const props = defineProps<{
  weather: WeatherCurrent;
  location: GeoLocation;
}>();

const weatherInfo = computed(() => getWeatherInfo(props.weather.weatherCode));

const currentDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

const uvLabel = computed(() => {
  const uv = props.weather.uvIndex;
  if (uv <= 2) return `${uv} (Low)`;
  if (uv <= 5) return `${uv} (Moderate)`;
  if (uv <= 7) return `${uv} (High)`;
  if (uv <= 10) return `${uv} (Very High)`;
  return `${uv} (Extreme)`;
});
</script>