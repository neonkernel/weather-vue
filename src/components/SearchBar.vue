<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  detectingLocation?: boolean
}>()

const emit = defineEmits<{
  search: [city: string]
  'use-my-location': []
}>()

const query = ref('')

function handleSubmit() {
  const trimmed = query.value.trim()
  if (!trimmed) return
  emit('search', trimmed)
  query.value = ''
}

function handleUseMyLocation() {
  emit('use-my-location')
}
</script>

<template>
  <div class="flex flex-col sm:flex-row gap-3">
    <!-- Search Input -->
    <div class="flex flex-1 gap-2">
      <div class="relative flex-1">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg
            class="w-5 h-5 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <input
          v-model="query"
          type="text"
          placeholder="Search for a city..."
          class="w-full pl-10 pr-4 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          @keydown.enter="handleSubmit"
        />
      </div>
      <button
        type="button"
        :disabled="!query.trim()"
        class="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        @click="handleSubmit"
      >
        Search
      </button>
    </div>

    <!-- Use My Location Button -->
    <button
      type="button"
      :disabled="detectingLocation"
      class="flex items-center justify-center gap-2 px-4 py-3 bg-slate-800/60 hover:bg-slate-700/80 disabled:opacity-60 disabled:cursor-not-allowed border border-slate-700 hover:border-blue-500 text-slate-300 hover:text-white font-medium rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 whitespace-nowrap"
      title="Use my current location"
      @click="handleUseMyLocation"
    >
      <!-- Spinner when detecting -->
      <svg
        v-if="detectingLocation"
        class="w-5 h-5 animate-spin text-blue-400"
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
      <!-- Location icon when idle -->
      <svg
        v-else
        class="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
        />
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
      <span>{{ detectingLocation ? 'Detecting...' : 'Use My Location' }}</span>
    </button>
  </div>
</template>