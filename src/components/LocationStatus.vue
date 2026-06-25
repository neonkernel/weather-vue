<script setup lang="ts">
import type { LocationSource } from '../stores/locationStore'

const props = defineProps<{
  cityName: string
  source: LocationSource
  loading?: boolean
}>()

const sourceConfig: Record<LocationSource, { label: string; icon: string; color: string }> = {
  geo: {
    label: 'GPS',
    icon: '📍',
    color: 'bg-green-500/20 text-green-300 border-green-500/30',
  },
  search: {
    label: 'Search',
    icon: '🔍',
    color: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
  default: {
    label: 'Default',
    icon: '🌍',
    color: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  },
}
</script>

<template>
  <div class="flex items-center">
    <!-- Loading state -->
    <div
      v-if="loading"
      class="flex items-center gap-2 px-3 py-1.5 rounded-full border bg-yellow-500/20 text-yellow-300 border-yellow-500/30 text-sm font-medium animate-pulse"
    >
      <svg
        class="w-4 h-4 animate-spin"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span>Detecting location...</span>
    </div>

    <!-- Normal state -->
    <div
      v-else-if="cityName"
      :class="[
        'flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium',
        sourceConfig[source]?.color ?? sourceConfig.default.color,
      ]"
    >
      <span>{{ sourceConfig[source]?.icon ?? '🌍' }}</span>
      <span class="max-w-[200px] truncate">{{ cityName }}</span>
      <span
        class="text-xs opacity-60 border-l border-current pl-2 ml-0.5"
      >
        {{ sourceConfig[source]?.label ?? 'Default' }}
      </span>
    </div>
  </div>
</template>