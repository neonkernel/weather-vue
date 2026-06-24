<template>
  <div
    v-if="locationStore.cityName"
    class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
    :class="pillClasses"
    :title="pillTitle"
  >
    <span class="text-sm">{{ sourceIcon }}</span>
    <span>{{ locationStore.cityName }}</span>
    <span v-if="sourceLabel" class="opacity-70">· {{ sourceLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLocationStore } from '../stores/locationStore'

const locationStore = useLocationStore()

const sourceIcon = computed(() => {
  switch (locationStore.source) {
    case 'geo':
      return '📍'
    case 'search':
      return '🔍'
    case 'default':
      return '🌐'
    default:
      return '🌐'
  }
})

const sourceLabel = computed(() => {
  switch (locationStore.source) {
    case 'geo':
      return 'GPS'
    case 'search':
      return 'Search'
    case 'default':
      return 'Default'
    default:
      return ''
  }
})

const pillTitle = computed(() => {
  switch (locationStore.source) {
    case 'geo':
      return 'Location detected automatically via GPS'
    case 'search':
      return 'Location set via search'
    case 'default':
      return 'Showing default location'
    default:
      return ''
  }
})

const pillClasses = computed(() => {
  switch (locationStore.source) {
    case 'geo':
      return 'bg-green-500/20 text-green-300 border border-green-500/30'
    case 'search':
      return 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
    case 'default':
      return 'bg-gray-500/20 text-gray-300 border border-gray-500/30'
    default:
      return 'bg-gray-500/20 text-gray-300 border border-gray-500/30'
  }
})
</script>