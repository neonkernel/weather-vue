<template>
  <div class="w-full max-w-xl mx-auto">
    <form
      @submit.prevent="handleSubmit"
      class="flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl px-4 py-3 shadow-lg"
    >
      <!-- Search Icon -->
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
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
        />
      </svg>

      <!-- Input -->
      <input
        v-model="inputValue"
        type="text"
        placeholder="Search for a city..."
        class="flex-1 bg-transparent text-white placeholder-white/50 outline-none text-base"
        :disabled="loading"
        aria-label="City name"
        autocomplete="off"
        @keydown.enter.prevent="handleSubmit"
      />

      <!-- Clear button -->
      <button
        v-if="inputValue && !loading"
        type="button"
        class="text-white/50 hover:text-white transition-colors p-1 rounded"
        aria-label="Clear search"
        @click="clearInput"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Submit Button -->
      <button
        type="submit"
        class="flex-shrink-0 bg-white/20 hover:bg-white/30 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-1.5 rounded-xl transition-all duration-200 text-sm"
        :disabled="loading || !inputValue.trim()"
        aria-label="Search"
      >
        <span v-if="loading" class="flex items-center gap-1.5">
          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Searching
        </span>
        <span v-else>Search</span>
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Props {
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const emit = defineEmits<{
  (e: 'search', city: string): void;
}>();

const inputValue = ref('');

function handleSubmit() {
  const trimmed = inputValue.value.trim();
  if (!trimmed || props.loading) return;
  emit('search', trimmed);
}

function clearInput() {
  inputValue.value = '';
}
</script>