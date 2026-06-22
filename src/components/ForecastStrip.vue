<script setup lang="ts">
import type { ForecastDay } from '@/types/weather'
import ForecastCard from '@/components/ForecastCard.vue'

defineProps<{
  days: ForecastDay[]
}>()
</script>

<template>
  <div
    class="glass-card p-4 sm:p-6"
    role="list"
    aria-label="7-day weather forecast"
  >
    <div class="flex gap-3 overflow-x-auto forecast-scroll pb-1">
      <ForecastCard
        v-for="day in days"
        :key="day.date"
        :day="day"
        role="listitem"
        class="flex-shrink-0"
      />
    </div>
  </div>
</template>