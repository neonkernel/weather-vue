<script setup lang="ts">
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  day: ForecastDay
}>()

/**
 * Returns a Tailwind text colour class based on precipitation chance.
 */
function precipColour(chance: number): string {
  if (chance >= 70) return 'text-blue-300'
  if (chance >= 40) return 'text-blue-200'
  return 'text-white/50'
}
</script>

<template>
  <article
    class="glass-card flex flex-col items-center gap-2 px-4 py-4 w-28 sm:w-32 cursor-default
           select-none transition-transform duration-200 hover:-translate-y-1 hover:shadow-lg"
    :aria-label="`${props.day.dayLabel}: ${props.day.condition}, high ${props.day.maxTempC}°C low ${props.day.minTempC}°C`"
  >
    <!-- Day label -->
    <p class="text-white/80 text-xs font-semibold uppercase tracking-wider">
      {{ props.day.dayLabel }}
    </p>

    <!-- Weather icon -->
    <span
      class="weather-icon text-4xl leading-none"
      :title="props.day.condition"
      aria-hidden="true"
    >
      {{ props.day.conditionIcon }}
    </span>

    <!-- Condition -->
    <p class="text-white/70 text-xs text-center leading-tight line-clamp-2">
      {{ props.day.condition }}
    </p>

    <!-- High / Low temps -->
    <div class="flex items-baseline gap-1.5 mt-auto">
      <span class="text-white font-bold text-base tabular-nums">
        {{ props.day.maxTempC }}°
      </span>
      <span class="text-white/50 text-sm tabular-nums">
        {{ props.day.minTempC }}°
      </span>
    </div>

    <!-- Precipitation chance -->
    <div
      class="flex items-center gap-1 text-xs font-medium"
      :class="precipColour(props.day.precipChance)"
      :title="`Precipitation: ${props.day.precipChance}% · ${props.day.precipMm} mm`"
    >
      <span aria-hidden="true">💧</span>
      <span>{{ props.day.precipChance }}%</span>
    </div>
  </article>
</template>