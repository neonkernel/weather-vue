<template>
  <div
    class="flex flex-col items-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/10 rounded-2xl px-4 py-4 transition-all duration-200 cursor-default min-w-[90px]"
  >
    <!-- Day label -->
    <span class="text-white/70 text-xs font-medium uppercase tracking-wide">{{ dayLabel }}</span>

    <!-- Weather emoji -->
    <span class="text-2xl" :title="weatherInfo.label" aria-label="weatherInfo.label">
      {{ weatherInfo.emoji }}
    </span>

    <!-- Temp range -->
    <div class="flex items-center gap-1 text-sm font-semibold text-white">
      <span>{{ day.tempMax }}°</span>
      <span class="text-white/40">/</span>
      <span class="text-white/60">{{ day.tempMin }}°</span>
    </div>

    <!-- Precipitation probability -->
    <div
      v-if="day.precipitationProbabilityMax > 0"
      class="flex items-center gap-1 text-xs text-blue-300"
    >
      <span>💧</span>
      <span>{{ day.precipitationProbabilityMax }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { DailyForecastData } from '../services/weatherService';
import { getWeatherInfo } from '../utils/weatherCodeMap';
import { formatDay } from '../utils/unitConverters';

interface Props {
  day: DailyForecastData;
}

const props = defineProps<Props>();

const weatherInfo = computed(() => getWeatherInfo(props.day.weatherCode));
const dayLabel = computed(() => formatDay(props.day.date));
</script>