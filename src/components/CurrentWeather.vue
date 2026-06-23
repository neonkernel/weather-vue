<template>
  <div
    class="
      relative overflow-hidden rounded-3xl
      bg-gradient-to-br from-sky-500/30 to-indigo-600/30
      backdrop-blur-md border border-white/10
      p-6 sm:p-8
    "
  >
    <!-- Background decoration -->
    <div
      class="absolute -top-8 -right-8 text-9xl opacity-10 select-none pointer-events-none"
      aria-hidden="true"
    >
      {{ weather.weatherEmoji }}
    </div>

    <!-- Location -->
    <div class="flex items-center gap-2 mb-4">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4 text-sky-300 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
        />
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      <h2 class="text-sky-200 font-medium text-sm tracking-wide">
        {{ locationName }}
      </h2>
    </div>

    <!-- Main temperature row -->
    <div class="flex items-end gap-4 mb-6">
      <div>
        <div class="flex items-start leading-none">
          <span class="text-7xl sm:text-8xl font-thin text-white">{{ weather.temperature }}</span>
          <span class="text-3xl font-light text-sky-300 mt-2">°C</span>
        </div>
        <p class="text-slate-300 mt-2 text-lg font-light">{{ weather.weatherLabel }}</p>
      </div>
      <div class="mb-3 text-6xl" aria-hidden="true">{{ weather.weatherEmoji }}</div>
    </div>

    <!-- Feels like -->
    <p class="text-slate-400 text-sm mb-6">
      Feels like
      <span class="text-white font-medium">{{ weather.feelsLike }}°C</span>
    </p>

    <!-- Stats grid -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard
        label="Humidity"
        :value="`${weather.humidity}%`"
        icon="💧"
      />
      <StatCard
        label="Wind"
        :value="`${weather.windSpeed} km/h`"
        icon="💨"
      />
      <StatCard
        label="Rain Chance"
        :value="`${weather.precipitationProbability}%`"
        icon="🌧️"
      />
      <StatCard
        label="UV Index"
        :value="String(Math.round(weather.uvIndex))"
        :badge="uvBadge"
        icon="☀️"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { WeatherCurrent } from '../types/weather';
import StatCard from './StatCard.vue';

const props = defineProps<{
  weather: WeatherCurrent;
  locationName: string;
}>();

const uvBadge = computed(() => {
  const uv = props.weather.uvIndex;
  if (uv <= 2) return { label: 'Low', color: 'green' };
  if (uv <= 5) return { label: 'Moderate', color: 'yellow' };
  if (uv <= 7) return { label: 'High', color: 'orange' };
  if (uv <= 10) return { label: 'Very High', color: 'red' };
  return { label: 'Extreme', color: 'purple' };
});
</script>