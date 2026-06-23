<template>
  <div class="w-full max-w-xl mx-auto">
    <form
      @submit.prevent="handleSubmit"
      class="flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl px-4 py-3 shadow-lg"
    >
      <!-- Search icon -->
      <svg
        class="w-5 h-5 text-white/60 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
        />
      </svg>

      <!-- Input -->
      <input
        v-model="query"
        type="text"
        placeholder="Search city (e.g. London, Tokyo, New York…)"
        class="flex-1 bg-transparent text-white placeholder-white/50 outline-none text-sm sm:text-base"
        :disabled="loading"
        aria-label="City name"
        autocomplete="off"
        autocorrect="off"
        spellcheck="false"
      />

      <!-- Clear button -->
      <button
        v-if="query.length > 0"
        type="button"
        @click="clearQuery"
        class="text-white/50 hover:text-white transition-colors flex-shrink-0"
        aria-label="Clear search"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Submit button -->
      <button
        type="submit"
        :disabled="loading || !query.trim()"
        class="flex-shrink-0 bg-white/20 hover:bg-white/30 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-1.5 rounded-xl transition-colors"
        aria-label="Search"
      >
        <span v-if="!loading">Search</span>
        <span v-else class="flex items-center gap-1.5">
          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Searching…
        </span>
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'search', city: string): void;
}>();

const query = ref('');

function handleSubmit() {
  const trimmed = query.value.trim();
  if (trimmed && !props.loading) {
    emit('search', trimmed);
  }
}

function clearQuery() {
  query.value = '';
}
</script>