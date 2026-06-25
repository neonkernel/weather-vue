<template>
  <div class="flex flex-col gap-2 w-full">
    <div class="flex gap-2 w-full">
      <div class="relative flex-1">
        <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
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
          placeholder="Search city..."
          class="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:border-white/40 focus:bg-white/15 transition-all text-sm"
          @keydown.enter="handleSearch"
          :disabled="isLoading"
        />
      </div>

      <button
        @click="handleSearch"
        :disabled="isLoading || !query.trim()"
        class="px-4 py-2.5 rounded-xl bg-white/20 hover:bg-white/30 border border-white/20 text-white text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
      >
        <span v-if="isLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        <span v-else>Search</span>
      </button>

      <!-- Use My Location button -->
      <button
        @click="handleGeolocate"
        :disabled="geoLoading"
        :title="geoLoading ? 'Detecting location...' : 'Use my location'"
        class="px-3 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        aria-label="Use my location"
      >
        <span v-if="geoLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          class="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
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

    <!-- Geo status message -->
    <p v-if="geoLoading" class="text-xs text-gray-400 text-center animate-pulse">
      📍 Detecting your location...
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isLoading?: boolean
  geoLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'search', query: string): void
  (e: 'geolocate'): void
}>()

const query = ref('')

function handleSearch() {
  const trimmed = query.value.trim()
  if (!trimmed || props.isLoading) return
  emit('search', trimmed)
}

function handleGeolocate() {
  if (props.geoLoading) return
  emit('geolocate')
}
</script>