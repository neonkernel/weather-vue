<template>
  <div class="w-full">
    <div class="flex gap-2">
      <div class="relative flex-1">
        <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <svg
            class="w-5 h-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <input
          v-model="query"
          type="text"
          placeholder="Search for a city..."
          class="w-full pl-10 pr-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all"
          @keydown.enter="handleSearch"
          @input="handleInput"
        />
      </div>

      <button
        @click="handleSearch"
        class="px-5 py-3 rounded-xl bg-blue-500 hover:bg-blue-400 text-white font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="!query.trim()"
      >
        Search
      </button>

      <button
        @click="handleGeolocate"
        :disabled="geoLoading"
        class="flex items-center justify-center w-12 h-12 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white transition-all focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
        :title="geoLoading ? 'Detecting location...' : 'Use My Location'"
        aria-label="Use my current location"
      >
        <svg
          v-if="!geoLoading"
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0013 3.06V1h-2v2.06A8.994 8.994 0 003.06 11H1v2h2.06A8.994 8.994 0 0011 20.94V23h2v-2.06A8.994 8.994 0 0020.94 13H23v-2h-2.06z"
          />
        </svg>
        <svg
          v-else
          class="w-5 h-5 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </button>
    </div>

    <p
      v-if="geoLoading"
      class="mt-2 text-xs text-blue-300 flex items-center gap-1.5"
    >
      <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      Detecting location...
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  geoLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'search', city: string): void
  (e: 'geolocate'): void
}>()

const query = ref('')

function handleSearch() {
  const trimmed = query.value.trim()
  if (!trimmed) return
  emit('search', trimmed)
  query.value = ''
}

function handleInput() {
  // Could add debounced autocomplete here in the future
}

function handleGeolocate() {
  emit('geolocate')
}
</script>