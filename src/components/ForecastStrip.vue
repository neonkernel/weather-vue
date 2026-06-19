<script setup lang="ts">
  import type { ForecastDay } from '@/types/weather'
  import ForecastCard from '@/components/ForecastCard.vue'

  interface Props {
    forecast: ForecastDay[]
  }

  const props = defineProps<Props>()
</script>

<template>
  <div class="w-full">
    <!-- Scrollable strip on small screens, flex wrap on larger -->
    <div
      class="flex gap-2 overflow-x-auto scrollbar-hide pb-1 md:grid md:grid-cols-7 md:overflow-visible"
      role="list"
      aria-label="7-day forecast"
    >
      <ForecastCard
        v-for="(day, index) in props.forecast"
        :key="day.date"
        :day="day"
        :is-today="index === 0"
        role="listitem"
      />
    </div>
  </div>
</template>