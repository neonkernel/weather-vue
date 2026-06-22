<template>
  <div
    class="glass-card-hover flex w-24 flex-col items-center gap-2 rounded-xl px-3 py-4 sm:w-auto"
    :class="{ 'border-weather-accent/40 bg-white/15': isToday }"
  >
    <!-- Day Label -->
    <p
      class="text-xs font-semibold uppercase tracking-wider"
      :class="isToday ? 'text-weather-accent' : 'text-white/60'"
    >
      {{ day.dayLabel }}
    </p>

    <!-- Weather Icon -->
    <span class="text-3xl leading-none" role="img" :aria-label="day.condition">
      {{ day.icon }}
    </span>

    <!-- Condition -->
    <p class="text-center text-xs leading-tight text-white/50">
      {{ day.condition }}
    </p>

    <!-- High / Low Temps -->
    <div class="flex flex-col items-center gap-0.5">
      <span class="text-sm font-bold text-white">{{ day.high }}°</span>
      <span class="text-xs text-white/40">{{ day.low }}°</span>
    </div>

    <!-- Precipitation Chance -->
    <div
      v-if="day.precipChance > 0"
      class="flex items-center gap-1"
      :title="`${day.precipChance}% chance of precipitation`"
    >
      <span class="text-xs" aria-hidden="true">🌧</span>
      <span class="text-xs font-medium text-blue-300">{{ day.precipChance }}%</span>
    </div>
    <div v-else class="h-4" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  day: ForecastDay
}>()

const isToday = computed(() => props.day.dayLabel === 'Today')
</script>