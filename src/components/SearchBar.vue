<template>
  <div class="w-full">
    <form @submit.prevent="handleSubmit" class="flex items-center gap-2">
      <!-- Search input group -->
      <div class="relative flex-1">
        <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <svg
            class="w-4 h-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
        </div>

        <input
          v-model="query"
          type="text"
          placeholder="Search city..."
          class="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all duration-200"
          :disabled="isLoading"
        />
      </div>

      <!-- Search button -->
      <button
        type="submit"
        :disabled="isLoading || !query.trim()"
        class="px-4 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-all duration-200 flex items-center gap-2 whitespace-nowrap"
      >
        <span>Search</span>
      </button>

      <!-- Use My Location button -->
      <button
        type="button"
        @click="handleUseLocation"
        :disabled="geoLoading || isLoading"
        :title="geoLoading ? 'Detecting location...' : 'Use my current location'"
        class="flex-shrink-0 p-2.5 rounded-xl border border-white/20 bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all duration-200 relative"
      >
        <!-- Spinner when loading -->
        <svg
          v-if="geoLoading"
          class="w-5 h-5 animate-spin text-blue-300"
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

        <!-- Location pin icon -->
        <svg
          v-else
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
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
      </button>
    </form>

    <!-- Geo status message -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <p v-if="geoLoading" class="mt-2 text-xs text-blue-300/80 flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse inline-block"></span>
        Detecting your location...
      </p>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isLoading?: boolean
  geoLoading?: boolean
}>()

const emit = defineEmits<{
  search: [city: string]
  useLocation: []
}>()

const query = ref('')

function handleSubmit() {
  const trimmed = query.value.trim()
  if (trimmed) {
    emit('search', trimmed)
  }
}

function handleUseLocation() {
  emit('useLocation')
}
</script>