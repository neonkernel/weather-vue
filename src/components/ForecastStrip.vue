<script setup lang="ts">
import ForecastCard from '@/components/ForecastCard.vue'
import type { ForecastDay } from '@/types/weather'

defineProps<{
  forecast: ForecastDay[]
}>()
</script>

<template>
  <div class="glass-card p-4">
    <!-- Scrollable row of forecast cards -->
    <div
      class="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory scrollbar-thin"
      role="list"
      aria-label="7-day weather forecast"
    >
      <ForecastCard
        v-for="day in forecast"
        :key="day.date"
        :day="day"
        class="snap-start"
        role="listitem"
      />
    </div>
  </div>
</template>