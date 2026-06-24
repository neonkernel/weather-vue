<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
  >
    <div v-if="cityName" class="flex items-center gap-2">
      <!-- Source icon + pill -->
      <div
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border"
        :class="pillClasses"
      >
        <!-- Geo icon -->
        <svg
          v-if="source === 'geo'"
          class="w-3.5 h-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
          />
        </svg>

        <!-- Search icon -->
        <svg
          v-else-if="source === 'search'"
          class="w-3.5 h-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>

        <!-- Default / globe icon -->
        <svg
          v-else
          class="w-3.5 h-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"
          />
        </svg>

        <span>{{ cityName }}</span>
        <span class="opacity-50">·</span>
        <span class="opacity-70">{{ sourceLabel }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LocationSource } from '../stores/locationStore'

const props = defineProps<{
  cityName: string
  source: LocationSource
}>()

const sourceLabel = computed(() => {
  switch (props.source) {
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

const pillClasses = computed(() => {
  switch (props.source) {
    case 'geo':
      return 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300'
    case 'search':
      return 'bg-blue-500/15 border-blue-400/30 text-blue-300'
    case 'default':
      return 'bg-slate-500/15 border-slate-400/30 text-slate-300'
    default:
      return 'bg-slate-500/15 border-slate-400/30 text-slate-300'
  }
})
</script>