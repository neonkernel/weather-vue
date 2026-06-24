<template>
  <div
    v-if="locationStore.cityName"
    class="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium backdrop-blur-sm transition-all duration-300"
    :class="pillClass"
    :title="tooltipText"
  >
    <!-- Source icon -->
    <component :is="'span'" class="flex-shrink-0">
      <!-- Geo icon -->
      <svg
        v-if="locationStore.source === 'geo'"
        xmlns="http://www.w3.org/2000/svg"
        class="h-3.5 w-3.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
      </svg>

      <!-- Search icon -->
      <svg
        v-else-if="locationStore.source === 'search'"
        xmlns="http://www.w3.org/2000/svg"
        class="h-3.5 w-3.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>

      <!-- Default/pin icon -->
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        class="h-3.5 w-3.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    </component>

    <span class="max-w-[160px] truncate">{{ displayName }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLocationStore } from '../stores/locationStore'

const locationStore = useLocationStore()

const pillClass = computed(() => {
  switch (locationStore.source) {
    case 'geo':
      return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
    case 'search':
      return 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
    default:
      return 'bg-white/10 text-white/60 border border-white/20'
  }
})

const displayName = computed(() => {
  if (!locationStore.cityName) {
    const lat = locationStore.lat?.toFixed(2)
    const lon = locationStore.lon?.toFixed(2)
    return lat && lon ? `${lat}, ${lon}` : 'Unknown'
  }
  return locationStore.cityName
})

const tooltipText = computed(() => {
  const sourceLabels = {
    geo: 'Detected via GPS',
    search: 'Manually searched',
    default: 'Default location',
  }
  return `${sourceLabels[locationStore.source]}: ${displayName.value}`
})
</script>