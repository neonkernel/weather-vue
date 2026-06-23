<template>
  <div
    class="
      flex flex-col sm:flex-row items-start sm:items-center gap-4
      bg-red-500/15 border border-red-400/40 rounded-2xl
      px-5 py-4 w-full max-w-lg mx-auto
    "
    role="alert"
    aria-live="assertive"
  >
    <!-- Icon -->
    <div class="flex-shrink-0 text-red-400 mt-0.5" aria-hidden="true">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
    </div>

    <!-- Text -->
    <div class="flex-1 min-w-0">
      <p class="text-red-300 font-semibold text-sm">{{ title }}</p>
      <p class="text-red-200/80 text-sm mt-0.5 break-words">{{ message }}</p>
    </div>

    <!-- Retry button -->
    <button
      v-if="showRetry"
      @click="emit('retry')"
      class="
        flex-shrink-0 flex items-center gap-1.5
        text-sm font-medium text-red-300 hover:text-white
        bg-red-400/20 hover:bg-red-400/40
        px-3 py-1.5 rounded-lg transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-red-400/60
      "
      aria-label="Retry"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M4 4v5h.582M20 20v-5h-.581M5.635 19A9 9 0 1 0 4.582 9H4"
        />
      </svg>
      Retry
    </button>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    message: string;
    title?: string;
    showRetry?: boolean;
  }>(),
  {
    title: 'Something went wrong',
    showRetry: true,
  }
);

const emit = defineEmits<{
  (e: 'retry'): void;
}>();
</script>