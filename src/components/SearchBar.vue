<template>
  <div class="flex gap-2">
    <div class="relative flex-1">
      <input
        v-model="query"
        type="text"
        placeholder="Search for a city..."
        class="w-full px-4 py-3 pl-10 rounded-xl bg-white/10 border border-white/20 text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur transition"
        @keydown.enter="handleSearch"
        @input="onInput"
      />
      <span class="absolute left-3 top-1/2 -translate-y-1/2 text-blue-300 pointer-events-none">
        🔍
      </span>
    </div>

    <button
      type="button"
      class="px-4 py-3 rounded-xl bg-blue-500 hover:bg-blue-400 active:bg-blue-600 text-white font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="!query.trim()"
      @click="handleSearch"
    >
      Search
    </button>

    <!-- Use My Location Button -->
    <button
      type="button"
      title="Use my current location"
      class="flex items-center justify-center px-4 py-3 rounded-xl bg-white/10 border border-white/20 hover:bg-white/20 active:bg-white/30 text-white transition focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
      :disabled="isLoading"
      @click="$emit('use-my-location')"
    >
      <svg
        v-if="!isLoading"
        class="w-5 h-5"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        viewBox="0 0 24 24"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        <circle cx="12" cy="12" r="8" stroke-dasharray="2 2" />
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
      <span class="ml-2 text-sm hidden sm:inline">My Location</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isLoading?: boolean
}>()

const emit = defineEmits<{
  search: [city: string]
  'use-my-location': []
}>()

const query = ref('')

function handleSearch() {
  const trimmed = query.value.trim()
  if (trimmed) {
    emit('search', trimmed)
  }
}

function onInput() {
  // Could add debounced suggestions here in future
}
</script>