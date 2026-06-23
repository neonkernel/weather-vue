<template>
  <div
    class="flex items-start gap-4 bg-red-500/20 border border-red-400/40 backdrop-blur-sm rounded-2xl p-5 text-white shadow-lg max-w-xl mx-auto"
    role="alert"
    aria-live="assertive"
  >
    <!-- Error icon -->
    <div class="flex-shrink-0 mt-0.5">
      <svg
        class="w-6 h-6 text-red-300"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
    </div>

    <!-- Message -->
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-red-100 text-sm sm:text-base">{{ title }}</p>
      <p class="text-red-200/90 text-sm mt-0.5 break-words">{{ message }}</p>
    </div>

    <!-- Retry button -->
    <button
      v-if="showRetry"
      @click="emit('retry')"
      class="flex-shrink-0 flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white/90 hover:text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
      aria-label="Retry"
    >
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      Retry
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string;
  title?: string;
  showRetry?: boolean;
}>();

withDefaults(defineProps<{
  message: string;
  title?: string;
  showRetry?: boolean;
}>(), {
  title: 'Something went wrong',
  showRetry: true,
});

const emit = defineEmits<{
  (e: 'retry'): void;
}>();
</script>