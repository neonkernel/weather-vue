<template>
  <div class="w-full">
    <div class="flex items-center gap-2">
      <div class="relative flex-1">
        <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <svg
            class="w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
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
          class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition shadow-sm"
          @keyup.enter="handleSearch"
          :disabled="loading"
          aria-label="Search for a city"
        />
      </div>

      <button
        @click="handleSearch"
        :disabled="loading || !query.trim()"
        class="px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-xl font-medium transition shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 whitespace-nowrap"
        aria-label="Search"
      >
        Search
      </button>

      <button
        @click="handleUseMyLocation"
        :disabled="geoLoading"
        :title="geoLoading ? 'Detecting location...' : 'Use my current location'"
        class="flex items-center justify-center w-10 h-10 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm hover:bg-gray-50 disabled:opacity-50 transition shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 flex-shrink-0"
        aria-label="Use my location"
      >
        <span v-if="geoLoading" class="animate-spin text-base">⏳</span>
        <svg
          v-else
          class="w-5 h-5 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
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
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  loading?: boolean
  geoLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'search', city: string): void
  (e: 'useLocation'): void
}>()

const query = ref('')

function handleSearch() {
  const trimmed = query.value.trim()
  if (!trimmed || props.loading) return
  emit('search', trimmed)
}

function handleUseMyLocation() {
  if (props.geoLoading) return
  emit('useLocation')
}
</script>