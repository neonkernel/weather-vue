<template>
  <div
    class="forecast-card glass-card flex flex-col items-center gap-2 px-4 py-4 min-w-[90px] flex-shrink-0 cursor-default select-none"
    :class="{ 'ring-2 ring-white/30 ring-offset-0': isToday }"
    :aria-label="`${dayForecast.day}: ${dayForecast.condition}, high ${dayForecast.high}${unitSymbol}, low ${dayForecast.low}${unitSymbol}`"
  >
    <!-- Day label -->
    <span
      class="text-xs font-semibold uppercase tracking-widest"
      :class="isToday ? 'text-weather-accent' : 'text-white/65'"
    >
      {{ isToday ? 'Today' : dayForecast.day }}
    </span>

    <!-- Date -->
    <span class="text-white/40 text-xs -mt-1">{{ dayForecast.date }}</span>

    <!-- Weather icon -->
    <span
      class="text-3xl mt-1 mb-1"
      role="img"
      :aria-label="dayForecast.condition"
    >
      {{ dayForecast.icon }}
    </span>

    <!-- High temperature -->
    <span class="text-white font-semibold text-sm">
      {{ dayForecast.high }}{{ unitSymbol }}
    </span>

    <!-- Low temperature -->
    <span class="text-white/50 text-sm font-light">
      {{ dayForecast.low }}{{ unitSymbol }}
    </span>

    <!-- Precipitation chance bar -->
    <div class="w-full mt-2">
      <div class="flex items-center justify-between mb-1">
        <span class="text-white/35 text-xs">💧</span>
        <span class="text-white/45 text-xs">{{ dayForecast.precipitationChance }}%</span>
      </div>
      <div class="w-full h-1 bg-white/10 rounded-full overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-700"
          :class="precipBarClass"
          :style="{ width: `${dayForecast.precipitationChance}%` }"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  dayForecast: ForecastDay
  units: 'metric' | 'imperial'
  isToday?: boolean
}>()

const unitSymbol = computed(() => (props.units === 'metric' ? '°' : '°F'))

const precipBarClass = computed(() => {
  const chance = props.dayForecast.precipitationChance
  if (chance >= 70) return 'bg-blue-400'
  if (chance >= 40) return 'bg-sky-300'
  if (chance >= 20) return 'bg-sky-200/70'
  return 'bg-white/30'
})
</script>

<style scoped>
.forecast-card {
  /* Override the hover transform from glass-card to a lighter effect for cards */
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.forecast-card:hover {
  transform: translateY(-4px) scale(1.02);
}
</style>