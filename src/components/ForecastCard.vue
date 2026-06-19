<script setup lang="ts">
import type { ForecastDay } from '@/types/weather'
import { CONDITION_ICONS } from '@/types/weather'
import { computed } from 'vue'

interface Props {
  day: ForecastDay
  /** Whether this card represents today */
  isToday?: boolean
}

const props = defineProps<Props>()

const icon = computed(() => CONDITION_ICONS[props.day.conditionCode] ?? '🌡️')

// Precipitation badge colour
const precipClass = computed(() => {
  const p = props.day.precipitationChance
  if (p >= 70) return 'text-blue-200 bg-blue-500/30'
  if (p >= 40) return 'text-sky-200 bg-sky-500/20'
  return 'text-white/50 bg-white/10'
})
</script>

<template>
  <div
    class="glass-card flex flex-col items-center px-3 py-4 min-w-[88px] sm:min-w-[100px] cursor-default select-none"
    :class="isToday ? 'ring-2 ring-white/40' : ''"
    role="article"
    :aria-label="`${day.day} forecast: ${day.condition}, high ${day.high}°, low ${day.low}°`"
  >
    <!-- Day label -->
    <p class="text-xs font-bold tracking-wider uppercase text-white/80 mb-2">
      {{ day.day }}
    </p>

    <!-- Weather icon -->
    <div class="text-3xl mb-2" role="img" :aria-hidden="true">
      {{ icon }}
    </div>

    <!-- Precipitation chance -->
    <div
      class="text-xs font-semibold rounded-full px-2 py-0.5 mb-3"
      :class="precipClass"
    >
      {{ day.precipitationChance }}%
    </div>

    <!-- High temp -->
    <p class="text-white font-bold text-base leading-none">
      {{ day.high }}°
    </p>

    <!-- Divider -->
    <div class="w-6 h-px bg-white/20 my-1.5" />

    <!-- Low temp -->
    <p class="text-white/55 text-sm font-medium">
      {{ day.low }}°
    </p>
  </div>
</template>