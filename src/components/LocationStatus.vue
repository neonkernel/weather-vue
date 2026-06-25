<template>
  <div v-if="cityName" class="flex items-center gap-1.5">
    <span
      class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border"
      :class="pillClasses"
    >
      <span class="text-sm">{{ sourceIcon }}</span>
      <span>{{ cityName }}</span>
      <span
        v-if="source"
        class="opacity-60 text-xs"
      >({{ sourceLabel }})</span>
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
    default:
      return '🌍'
  }
})

const sourceLabel = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'GPS'
    case 'search':
      return 'search'
    case 'default':
    default:
      return 'default'
  }
})

const pillClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-500/10 border-green-500/30 text-green-300'
    case 'search':
      return 'bg-blue-500/10 border-blue-500/30 text-blue-300'
    case 'default':
    default:
      return 'bg-gray-500/10 border-gray-500/30 text-gray-300'
  }
})
</script>