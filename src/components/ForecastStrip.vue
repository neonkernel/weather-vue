<script setup lang="ts">
import type { ForecastDay } from '@/types/weather'
import ForecastCard from '@/components/ForecastCard.vue'

interface Props {
  forecast: ForecastDay[]
}

const props = defineProps<Props>()
</script>

<template>
  <div class="relative">
    <!-- Horizontal scrollable strip -->
    <div
      class="flex gap-3 overflow-x-auto scrollbar-hide pb-2 snap-x snap-mandatory"
      role="list"
      aria-label="7-day weather forecast"
    >
      <div
        v-for="(day, index) in props.forecast"
        :key="day.date"
        class="snap-start flex-shrink-0"
        role="listitem"
      >
        <ForecastCard
          :day="day"
          :is-today="index === 0"
        />
      </div>
    </div>

    <!-- Right fade gradient — indicates scrollability on mobile -->
    <div
      class="absolute top-0 right-0 h-full w-10 pointer-events-none sm:hidden"
      style="background: linear-gradient(to left, rgba(0,0,0,0.15), transparent)"
    />
  </div>
</template>