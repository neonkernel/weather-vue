<template>
  <div
    class="bg-white/10 backdrop-blur-sm border border-white/15 rounded-2xl p-4 flex flex-col items-center gap-2 text-white min-w-[100px] flex-1"
  >
    <!-- Day label -->
    <div class="text-white/60 text-xs font-medium uppercase tracking-wider">{{ dayLabel }}</div>

    <!-- Weather emoji -->
    <div class="text-3xl select-none" aria-hidden="true">{{ weatherInfo.emoji }}</div>

    <!-- Condition label -->
    <div class="text-xs text-white/70 text-center leading-tight">{{ weatherInfo.label }}</div>

    <!-- Temp range -->
    <div class="flex items-center gap-1.5 text-sm font-medium mt-1">
      <span class="text-white">{{ day.temperatureMax }}°</span>
      <span class="text-white/40">/</span>
      <span class="text-white/60">{{ day.temperatureMin }}°</span>
    </div>

    <!-- Precipitation -->
    <div v-if="day.precipitationSum > 0" class="text-xs text-blue-300/80 flex items-center gap-1">
      <span>💧</span>
      <span>{{ day.precipitationSum.toFixed(1) }}mm</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getWeatherInfo } from '../utils/weatherCodeMap';
import { formatDate } from '../utils/unitConverters';
import type { ForecastDay } from '../types/weather';

const props = defineProps<{
  day: ForecastDay;
  isToday?: boolean;
}>();

const weatherInfo = computed(() => getWeatherInfo(props.day.weatherCode));

const dayLabel = computed(() => {
  if (props.isToday) return 'Today';
  // Parse as local date to avoid off-by-one from UTC
  const date = new Date(props.day.date + 'T00:00:00');
  return date.toLocaleDateString('en-US', { weekday: 'short' });
});
</script>