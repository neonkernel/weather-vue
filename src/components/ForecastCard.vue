<script setup lang="ts">
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  day: ForecastDay
}>()

/**
 * Returns a Tailwind color class based on precipitation probability.
 */
function precipColor(prob: number): string {
  if (prob >= 70) return 'text-blue-300'
  if (prob >= 40) return 'text-blue-200'
  return 'text-white/40'
}

/**
 * Returns true if this card represents today.
 */
const isToday = props.day.day === 'Today'
</script>

<template>
  <article
    class="flex-shrink-0 flex flex-col items-center gap-2 px-4 py-4 rounded-xl transition-all duration-200 cursor-default select-none min-w-[90px]"
    :class="[
      isToday
        ? 'bg-white/20 border border-white/30 shadow-glow'
        : 'bg-white/06 border border-white/10 hover:bg-white/12 hover:border-white/20 hover:scale-105',
    ]"
    :aria-label="`${day.day}: ${day.condition}, high ${day.high}°, low ${day.low}°`"
  >
    <!-- Day label -->
    <span
      class="text-xs font-bold uppercase tracking-widest"
      :class="isToday ? 'text-weather-sun' : 'text-secondary'"
    >
      {{ day.day }}
    </span>

    <!-- Weather icon -->
    <span class="text-3xl leading-none" role="img" :aria-hidden="true">
      {{ day.icon }}
    </span>

    <!-- Condition label -->
    <span class="text-xs text-center text-muted leading-tight max-w-[80px]">
      {{ day.condition }}
    </span>

    <!-- Temp range -->
    <div class="flex items-center gap-1.5 mt-1">
      <span class="text-sm font-bold text-white">{{ day.high }}°</span>
      <span class="text-xs text-muted">|</span>
      <span class="text-sm text-secondary">{{ day.low }}°</span>
    </div>

    <!-- Precipitation probability -->
    <div
      v-if="day.precipProbability > 0"
      class="flex items-center gap-1"
      :class="precipColor(day.precipProbability)"
    >
      <span class="text-xs" aria-hidden="true">🌧️</span>
      <span class="text-xs font-medium">{{ day.precipProbability }}%</span>
    </div>
    <div v-else class="h-4" aria-hidden="true" />

  </article>
</template>