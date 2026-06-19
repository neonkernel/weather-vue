<template>
  <article
    class="forecast-card glass-card"
    :class="{ 'forecast-card--today': isToday }"
    :aria-label="`Forecast for ${props.day.day}: ${props.day.condition}, high of ${props.day.high}°C, low of ${props.day.low}°C`"
  >
    <!-- Day label -->
    <div class="forecast-card__day" :class="{ 'forecast-card__day--today': isToday }">
      {{ props.day.day }}
    </div>

    <!-- Weather icon -->
    <div
      class="forecast-card__icon"
      role="img"
      :aria-label="props.day.condition"
    >
      {{ props.day.icon }}
    </div>

    <!-- Precipitation chance -->
    <div
      v-if="props.day.precipitationChance > 0"
      class="forecast-card__precip"
      :title="`${props.day.precipitationChance}% chance of precipitation`"
    >
      <span aria-hidden="true">💧</span>
      <span>{{ props.day.precipitationChance }}%</span>
    </div>
    <div v-else class="forecast-card__precip forecast-card__precip--empty" aria-hidden="true">
      &nbsp;
    </div>

    <!-- Temperature range -->
    <div class="forecast-card__temps">
      <span
        class="forecast-card__high"
        :aria-label="`High: ${props.day.high}°C`"
      >
        {{ props.day.high }}°
      </span>
      <span
        class="forecast-card__low"
        :aria-label="`Low: ${props.day.low}°C`"
      >
        {{ props.day.low }}°
      </span>
    </div>

    <!-- Temperature range bar -->
    <div class="forecast-card__bar-wrapper" aria-hidden="true">
      <div
        class="forecast-card__bar"
        :style="barStyle"
      />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ForecastDay } from '@/types/weather'

const props = defineProps<{
  day: ForecastDay
}>()

const isToday = computed(() => props.day.day === 'Today')

/**
 * Compute bar fill based on temperature range relative to a fixed scale.
 * We map 0°C → 40°C to the bar width.
 */
const barStyle = computed(() => {
  const scale = { min: 0, max: 40 }
  const leftPct = ((props.day.low - scale.min) / (scale.max - scale.min)) * 100
  const rightPct = 100 - ((props.day.high - scale.min) / (scale.max - scale.min)) * 100
  return {
    marginLeft: `${Math.max(0, leftPct)}%`,
    marginRight: `${Math.max(0, rightPct)}%`,
  }
})
</script>

<style scoped>
.forecast-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0.75rem;
  min-width: 90px;
  cursor: default;
  transition:
    transform 200ms ease,
    box-shadow 200ms ease,
    background 200ms ease;
}

.forecast-card--today {
  background: rgba(86, 180, 233, 0.2);
  border-color: rgba(86, 180, 233, 0.4);
}

.forecast-card__day {
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.65);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.forecast-card__day--today {
  color: #56b4e9;
}

.forecast-card__icon {
  font-size: 2rem;
  line-height: 1;
  filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.25));
  transition: transform 200ms ease;
}

.forecast-card:hover .forecast-card__icon {
  transform: scale(1.15);
}

.forecast-card__precip {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  font-weight: 500;
  color: rgba(168, 216, 234, 0.9);
  min-height: 1.1rem;
}

.forecast-card__precip--empty {
  min-height: 1.1rem;
}

.forecast-card__temps {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}

.forecast-card__high {
  font-size: 1.1rem;
  font-weight: 700;
  color: white;
}

.forecast-card__low {
  font-size: 0.875rem;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.45);
}

/* Temperature range bar */
.forecast-card__bar-wrapper {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 2px;
  overflow: hidden;
}

.forecast-card__bar {
  height: 100%;
  background: linear-gradient(90deg, #56b4e9, #a8d8ea);
  border-radius: 2px;
  min-width: 4px;
}
</style>