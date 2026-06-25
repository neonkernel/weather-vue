<template>
  <div class="flex items-center justify-center">
    <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium backdrop-blur-sm border"
      :class="badgeClasses"
    >
      <span class="text-base leading-none">{{ sourceIcon }}</span>
      <span>{{ cityName }}</span>
      <span class="opacity-70 text-xs font-normal">{{ sourceLabel }}</span>
    </div>
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
    case 'geo': return '📍'
    case 'search': return '🔍'
    case 'default': return '🌍'
    default: return '📍'
  }
})

const sourceLabel = computed(() => {
  switch (props.source) {
    case 'geo': return '· GPS'
    case 'search': return '· Search'
    case 'default': return '· Default'
    default: return ''
  }
})

const badgeClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-green-500/20 border-green-400/30 text-green-200'
    case 'search':
      return 'bg-blue-500/20 border-blue-400/30 text-blue-200'
    case 'default':
      return 'bg-white/10 border-white/20 text-blue-200'
    default:
      return 'bg-white/10 border-white/20 text-blue-200'
  }
})
</script>