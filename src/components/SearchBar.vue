<template>
  <div class="flex gap-2">
    <div class="flex-1 relative">
      <input
        v-model="query"
        type="text"
        placeholder="Search city..."
        class="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm"
        @keyup.enter="handleSearch"
        :disabled="loading"
      />
    </div>

    <!-- Search Button -->
    <button
      @click="handleSearch"
      :disabled="loading || !query.trim()"
      class="px-5 py-3 bg-blue-500 hover:bg-blue-400 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors duration-200 flex items-center gap-2"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      Search
    </button>

    <!-- Use My Location Button -->
    <button
      @click="handleUseLocation"
      :disabled="loading"
      :title="loading ? 'Detecting location...' : 'Use my current location'"
      class="px-4 py-3 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed border border-white/20 text-white rounded-xl transition-colors duration-200 flex items-center gap-2 backdrop-blur-sm"
    >
      <svg
        v-if="!loading"
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <svg
        v-else
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5 animate-spin"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
      <span class="hidden sm:inline">{{ loading ? 'Detecting...' : 'My Location' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'search', city: string): void
  (e: 'use-location'): void
}>()

const query = ref('')

function handleSearch() {
  if (query.value.trim()) {
    emit('search', query.value.trim())
  }
}

function handleUseLocation() {
  emit('use-location')
}
</script>