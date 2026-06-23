<template>
  <form
    class="flex items-center gap-2 w-full max-w-lg mx-auto"
    @submit.prevent="handleSubmit"
    role="search"
    aria-label="Search for a city"
  >
    <div class="relative flex-1">
      <span class="absolute inset-y-0 left-3 flex items-center pointer-events-none text-slate-400">
        <!-- Search icon -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
          />
        </svg>
      </span>
      <input
        v-model="query"
        type="text"
        name="city"
        autocomplete="off"
        placeholder="Search city… e.g. London"
        class="
          w-full pl-10 pr-4 py-3 rounded-xl
          bg-white/10 backdrop-blur-sm
          border border-white/20
          text-white placeholder-slate-400
          focus:outline-none focus:ring-2 focus:ring-sky-400/70 focus:border-transparent
          transition-all duration-200
        "
        :disabled="props.loading"
        aria-label="City name"
      />
    </div>

    <button
      type="submit"
      :disabled="props.loading || !query.trim()"
      class="
        flex items-center gap-2 px-5 py-3 rounded-xl font-semibold
        bg-sky-500 hover:bg-sky-400 disabled:bg-sky-500/40
        text-white transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-sky-400/70
        disabled:cursor-not-allowed
      "
      aria-label="Search"
    >
      <span v-if="!props.loading">Search</span>
      <span v-else class="flex items-center gap-1">
        <svg
          class="animate-spin h-4 w-4 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
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
            d="M4 12a8 8 0 018-8v8H4z"
          />
        </svg>
        Searching…
      </span>
    </button>
  </form>
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
  if (!trimmed || props.loading) return;
  emit('search', trimmed);
}
</script>