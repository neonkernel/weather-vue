<template>
  <div v-if="cityName" class="flex items-center gap-1.5">
    <span
      class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border"
      :class="badgeClasses"
    >
      <span>{{ sourceIcon }}</span>
      <span>{{ cityName }}</span>
    </span>
    <span
      v-if="source !== 'default'"
      class="text-xs px-1.5 py-0.5 rounded-full font-medium"
      :class="sourceTagClasses"
    >
      {{ sourceLabel }}
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
      return '📍'
  }
})

const sourceLabel = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'GPS'
    case 'search':
      return 'Search'
    default:
      return ''
  }
})

const badgeClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-50 text-green-700 border-green-200'
    case 'search':
      return 'bg-blue-50 text-blue-700 border-blue-200'
    case 'default':
      return 'bg-gray-50 text-gray-600 border-gray-200'
    default:
      return 'bg-gray-50 text-gray-600 border-gray-200'
  }
})

const sourceTagClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-100 text-green-700'
    case 'search':
      return 'bg-blue-100 text-blue-700'
    default:
      return ''
  }
})
</script>