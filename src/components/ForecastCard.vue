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

  const icon = computed(() => CONDITION_ICONS[props.day.conditionCode])

  const precipLabel = computed(() =>
    props.day.precipChance > 0 ? `${props.day.precipChance}%` : null
  )
</script>

<template>
  <article
    class="glass-card forecast-card-hover flex flex-col items-center gap-2 px-3 py-4 min-w-[80px] flex-1"
    :class="{ 'ring-2 ring-white/40 bg-white/20': isToday }"
    :aria-label="`${day.dayLabel}: ${day.condition}, high ${day.tempHigh}°, low ${day.tempLow}°`"
  >
    <!-- Day label -->
    <span
      class="text-xs font-semibold uppercase tracking-wide"
      :class="isToday ? 'text-white' : 'text-white/70'"
    >
      {{ day.dayLabel }}
    </span>

    <!-- Condition icon -->
    <span class="text-2xl leading-none select-none" role="img" :aria-label="day.condition">
      {{ icon }}
    </span>

    <!-- Precipitation chance -->
    <span
      v-if="precipLabel"
      class="text-xs text-blue-200/80 font-medium flex items-center gap-0.5"
    >
      <span>💧</span>{{ precipLabel }}
    </span>
    <span v-else class="text-xs text-transparent select-none">—</span>

    <!-- High / Low -->
    <div class="flex flex-col items-center gap-0.5 mt-1">
      <span class="text-sm font-bold text-white">{{ day.tempHigh }}°</span>
      <span class="text-xs text-white/50">{{ day.tempLow }}°</span>
    </div>
  </article>
</template>