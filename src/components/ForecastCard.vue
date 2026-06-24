<template>
  <div
    class="flex flex-col items-center gap-1 rounded-xl border p-3 text-center backdrop-blur-sm"
    :class="isToday ? 'border-blue-400/40 bg-blue-500/15' : 'border-white/10 bg-white/5'"
  >
    <p class="text-xs font-medium" :class="isToday ? 'text-blue-300' : 'text-white/60'">
      {{ isToday ? 'Today' : dayLabel }}
    </p>
    <span class="text-2xl">{{ emoji }}</span>
    <p class="text-sm font-semibold text-white">{{ Math.round(tempMax) }}°</p>
    <p class="text-xs text-white/50">{{ Math.round(tempMin) }}°</p>
    <p v-if="precipitation > 0" class="text-xs text-blue-300">{{ precipitation }}mm</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getWeatherEmoji } from '../utils/weatherCodeMap'

const props = defineProps<{
  date: string
  weatherCode: number
  tempMax: number
  tempMin: number
  precipitation: number
  isToday?: boolean
}>()

const dayLabel = computed(() => {
  const d = new Date(props.date)
  return d.toLocaleDateString('en-US', { weekday: 'short' })
})

const emoji = computed(() => getWeatherEmoji(props.weatherCode, true))
</script>