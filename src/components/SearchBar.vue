<template>
  <div class="w-full max-w-xl mx-auto">
    <form
      @submit.prevent="handleSubmit"
      class="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-2xl p-2 border border-white/20 shadow-lg"
    >
      <div class="flex-1 flex items-center gap-2 px-3">
        <svg
          class="w-5 h-5 text-white/60 flex-shrink-0"
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
        <input
          v-model="inputValue"
          type="text"
          placeholder="Search for a city..."
          class="flex-1 bg-transparent text-white placeholder-white/50 outline-none text-base py-1"
          :disabled="loading"
          @keydown.escape="clearInput"
          aria-label="City name"
        />
        <button
          v-if="inputValue"
          type="button"
          @click="clearInput"
          class="text-white/50 hover:text-white transition-colors"
          aria-label="Clear search"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <button
        type="submit"
        :disabled="loading || !inputValue.trim()"
        class="
          flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm
          bg-white text-blue-600
          hover:bg-blue-50 active:scale-95
          disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100
          transition-all duration-150 shadow-sm
          flex-shrink-0
        "
        aria-label="Search"
      >
        <span v-if="loading" class="flex items-center gap-1.5">
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Searching
        </span>
        <span v-else>Search</span>
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'search', city: string): void
}>()

const inputValue = ref('')

function handleSubmit() {
  const trimmed = inputValue.value.trim()
  if (trimmed && !props.loading) {
    emit('search', trimmed)
  }
}

function clearInput() {
  inputValue.value = ''
}
</script>