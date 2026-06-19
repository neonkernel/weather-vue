<template>
  <div class="forecast-strip-wrapper">
    <div class="forecast-strip" role="list" aria-label="7-day weather forecast">
      <ForecastCard
        v-for="day in props.forecast"
        :key="day.date"
        :day="day"
        role="listitem"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import ForecastCard from '@/components/ForecastCard.vue'
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  forecast: ForecastDay[]
}>()
</script>

<style scoped>
.forecast-strip-wrapper {
  overflow-x: auto;
  /* Negative margin trick to allow cards to bleed to edge on mobile */
  margin: 0 -0.25rem;
  padding: 0 0.25rem;
  /* Hide scrollbar on Firefox */
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.forecast-strip {
  display: flex;
  gap: 0.75rem;
  padding-bottom: 0.5rem;
  /* Ensure cards don't shrink on smaller screens */
  min-width: min-content;
}

/* On larger screens, distribute cards evenly */
@media (min-width: 640px) {
  .forecast-strip {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    min-width: unset;
  }
}
</style>