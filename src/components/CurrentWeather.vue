<script setup lang="ts">
  import type { WeatherCurrent } from '@/types/weather'
  import { CONDITION_ICONS } from '@/types/weather'
  import { computed } from 'vue'

  interface Props {
    current: WeatherCurrent
  }

  const props = defineProps<Props>()

  const conditionIcon = computed(() => CONDITION_ICONS[props.current.conditionCode])

  const windLabel = computed(() => `${props.current.windSpeed} km/h ${props.current.windDirection}`)

  const stats = computed(() => [
    { label: 'Humidity', value: `${props.current.humidity}%`, icon: '💧' },
    { label: 'Wind', value: windLabel.value, icon: '💨' },
    { label: 'Visibility', value: `${props.current.visibility} km`, icon: '👁️' },
    { label: 'UV Index', value: String(props.current.uvIndex), icon: '☀️' },
    { label: 'Pressure', value: `${props.current.pressure} hPa`, icon: '🌡️' },
    { label: 'Sunrise', value: props.current.sunrise, icon: '🌅' },
    { label: 'Sunset', value: props.current.sunset, icon: '🌇' },
    { label: 'Feels Like', value: `${props.current.feelsLike}°`, icon: '🌡️' },
  ])
</script>

<template>
  <div class="glass-card p-6 md:p-8">
    <!-- Location + Condition -->
    <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
      <!-- Left: Temperature block -->
      <div class="flex items-start gap-5">
        <!-- Condition icon -->
        <div class="text-6xl md:text-7xl leading-none select-none" role="img" :aria-label="current.condition">
          {{ conditionIcon }}
        </div>

        <!-- Temp + location -->
        <div class="flex flex-col gap-1">
          <div class="flex items-end gap-1">
            <span class="temp-display text-7xl md:text-8xl text-white text-shadow-lg">
              {{ current.temperature }}
            </span>
            <span class="temp-display text-3xl md:text-4xl text-white/80 mb-3">°C</span>
          </div>
          <p class="text-white/80 text-xl font-medium text-shadow">
            {{ current.condition }}
          </p>
          <p class="text-white/60 text-base font-medium mt-0.5">
            {{ current.city }}, {{ current.country }}
          </p>
        </div>
      </div>

      <!-- Right: Stats grid -->
      <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-2 lg:grid-cols-4 gap-2 md:max-w-md w-full">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="stat-item"
        >
          <span class="text-xl leading-none" role="img" :aria-label="stat.label">{{ stat.icon }}</span>
          <span class="text-white text-sm font-semibold">{{ stat.value }}</span>
          <span class="text-white/50 text-xs">{{ stat.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>