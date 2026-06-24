<template>
  <div class="flex items-center gap-2">
    <span
      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur border"
      :class="badgeClasses"
    >
      <span class="text-sm">{{ sourceIcon }}</span>
      <span>{{ cityName }}</span>
      <span
        class="px-1.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide"
        :class="sourceTagClasses"
      >
        {{ sourceLabel }}
      </span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LocationSource } from '../stores/locationStore'

const props = defineProps<{
  cityName: string
  source: LocationSource
}>()

const sourceIcon = computed(() => {
  switch (props.source) {
    case 'geo':
      return '📍'
    case 'search':
      return '🔍'
    case 'default':
      return '🌍'
    default:
      return '🌍'
  }
})

const sourceLabel = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'GPS'
    case 'search':
      return 'Search'
    case 'default':
      return 'Default'
    default:
      return 'Unknown'
  }
})

const badgeClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-500/20 border-green-400/30 text-green-100'
    case 'search':
      return 'bg-blue-500/20 border-blue-400/30 text-blue-100'
    case 'default':
      return 'bg-gray-500/20 border-gray-400/30 text-gray-200'
    default:
      return 'bg-gray-500/20 border-gray-400/30 text-gray-200'
  }
})

const sourceTagClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-500/40 text-green-100'
    case 'search':
      return 'bg-blue-500/40 text-blue-100'
    case 'default':
      return 'bg-gray-500/40 text-gray-200'
    default:
      return 'bg-gray-500/40 text-gray-200'
  }
})
</script>