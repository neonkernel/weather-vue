<template>
  <div
    class="glass-card overflow-hidden p-4"
    role="list"
    aria-label="7-day forecast"
  >
    <div class="flex gap-3 overflow-x-auto pb-1 sm:grid sm:grid-cols-7 sm:gap-2 sm:overflow-visible sm:pb-0">
      <ForecastCard
        v-for="day in forecast"
        :key="day.date"
        :day="day"
        role="listitem"
        class="flex-shrink-0 sm:flex-shrink"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import ForecastCard from '@/components/ForecastCard.vue'
import type { ForecastDay } from '@/types/weather'

defineProps<{
  forecast: ForecastDay[]
}>()
</script>