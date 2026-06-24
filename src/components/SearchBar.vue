<template>
  <div class="relative w-full">
    <div class="flex items-center gap-2">
      <!-- Search input group -->
      <div class="relative flex-1">
        <div class="pointer-events-none absolute inset-y-0 left-3 flex items-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 text-white/40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>

        <input
          ref="inputRef"
          v-model="query"
          type="text"
          placeholder="Search city..."
          class="w-full rounded-xl border border-white/20 bg-white/10 py-2.5 pl-10 pr-4 text-sm text-white placeholder-white/40 backdrop-blur-sm transition-all duration-200 focus:border-white/40 focus:bg-white/15 focus:outline-none focus:ring-2 focus:ring-white/20"
          @input="onInput"
          @keydown.enter="onEnter"
          @keydown.escape="clearResults"
          @keydown.arrow-down.prevent="selectNext"
          @keydown.arrow-up.prevent="selectPrev"
        />

        <!-- Clear button -->
        <button
          v-if="query"
          type="button"
          class="absolute inset-y-0 right-3 flex items-center text-white/40 transition-colors hover:text-white/70"
          @click="clearQuery"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <!-- Use My Location button -->
      <button
        type="button"
        class="flex flex-shrink-0 items-center gap-1.5 rounded-xl border border-white/20 bg-white/10 px-3 py-2.5 text-sm text-white/70 backdrop-blur-sm transition-all duration-200 hover:bg-white/20 hover:text-white focus:outline-none focus:ring-2 focus:ring-white/20 disabled:cursor-not-allowed disabled:opacity-50"
        :title="geoLoading ? 'Detecting location...' : 'Use my current location'"
        :disabled="geoLoading"
        @click="triggerGeolocation"
      >
        <svg
          v-if="!geoLoading"
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        </svg>

        <!-- Spinner when loading -->
        <svg
          v-else
          class="h-4 w-4 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
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

        <span class="hidden sm:inline">
          {{ geoLoading ? 'Locating...' : 'My Location' }}
        </span>
      </button>
    </div>

    <!-- Autocomplete dropdown -->
    <Transition name="dropdown">
      <ul
        v-if="showDropdown && results.length"
        class="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-xl border border-white/20 bg-slate-800/95 shadow-2xl backdrop-blur-md"
        role="listbox"
      >
        <li
          v-for="(result, index) in results"
          :key="result.id"
          class="flex cursor-pointer items-center gap-3 px-4 py-3 text-sm transition-colors"
          :class="
            index === selectedIndex
              ? 'bg-white/20 text-white'
              : 'text-white/70 hover:bg-white/10 hover:text-white'
          "
          role="option"
          :aria-selected="index === selectedIndex"
          @click="selectResult(result)"
          @mouseenter="selectedIndex = index"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 flex-shrink-0 text-white/40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <div>
            <div class="font-medium text-white">{{ result.name }}</div>
            <div class="text-xs text-white/50">
              {{ [result.admin1, result.country].filter(Boolean).join(', ') }}
            </div>
          </div>
        </li>
      </ul>
    </Transition>

    <!-- No results -->
    <Transition name="dropdown">
      <div
        v-if="showDropdown && !results.length && !geocodingLoading && query.length >= 2"
        class="absolute left-0 right-0 top-full z-50 mt-1.5 rounded-xl border border-white/20 bg-slate-800/95 px-4 py-3 text-sm text-white/50 shadow-2xl backdrop-blur-md"
      >
        No cities found for "{{ query }}"
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useGeocoding } from '../composables/useGeocoding'
import type { GeocodingResult } from '../services/geocodingService'

const props = defineProps<{
  geoLoading?: boolean
}>()

const emit = defineEmits<{
  citySelected: [name: string, lat: number, lon: number]
  geolocate: []
}>()

const { results, loading: geocodingLoading, search, clearResults } = useGeocoding()

const query = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const selectedIndex = ref(-1)
const showDropdown = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const onInput = () => {
  selectedIndex.value = -1
  showDropdown.value = true

  if (debounceTimer) clearTimeout(debounceTimer)

  if (query.value.trim().length < 2) {
    clearResults()
    return
  }

  debounceTimer = setTimeout(() => {
    search(query.value.trim())
  }, 300)
}

const onEnter = () => {
  if (selectedIndex.value >= 0 && results.value[selectedIndex.value]) {
    selectResult(results.value[selectedIndex.value])
  } else if (results.value.length > 0) {
    selectResult(results.value[0])
  }
}

const selectResult = (result: GeocodingResult) => {
  query.value = result.name
  showDropdown.value = false
  clearResults()
  emit('citySelected', result.name, result.latitude, result.longitude)
}

const selectNext = () => {
  if (results.value.length === 0) return
  selectedIndex.value = (selectedIndex.value + 1) % results.value.length
}

const selectPrev = () => {
  if (results.value.length === 0) return
  selectedIndex.value =
    selectedIndex.value <= 0 ? results.value.length - 1 : selectedIndex.value - 1
}

const clearQuery = () => {
  query.value = ''
  clearResults()
  showDropdown.value = false
  inputRef.value?.focus()
}

const triggerGeolocation = () => {
  emit('geolocate')
}
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>