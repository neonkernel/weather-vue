<template>
  <div class="forecast-strip">
    <!-- Scrollable container for mobile -->
    <div
      class="flex gap-3 overflow-x-auto scrollbar-hide pb-2 -mx-1 px-1"
      role="list"
      aria-label="Weekly forecast"
    >
      <ForecastCard
        v-for="(day, index) in forecast"
        :key="day.date"
        :day-forecast="day"
        :units="units"
        :is-today="index === 0"
        :style="{ animationDelay: `${index * 60}ms` }"
        class="animate-slide-up"
        role="listitem"
      />
    </div>

    <!-- Precipitation legend -->
    <div class="flex items-center gap-2 mt-3 px-1">
      <span class="text-white/35 text-xs">💧 Precip. chance shown below each card</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import ForecastCard from '@/components/ForecastCard.vue'
import type { ForecastDay } from '@/types/weather'

defineProps<{
  forecast: ForecastDay[]
  units: 'metric' | 'imperial'
}>()
</script>