<template>
  <div
    role="alert"
    class="flex items-start gap-3 bg-red-500/20 border border-red-400/40 backdrop-blur-sm text-white rounded-2xl px-5 py-4 shadow-lg max-w-xl mx-auto"
  >
    <!-- Error Icon -->
    <div class="flex-shrink-0 mt-0.5">
      <svg
        class="w-5 h-5 text-red-300"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
    </div>

    <!-- Message -->
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-red-200 text-sm mb-0.5">Something went wrong</p>
      <p class="text-white/80 text-sm leading-relaxed">{{ message }}</p>
    </div>

    <!-- Retry Button -->
    <button
      v-if="showRetry"
      class="flex-shrink-0 bg-white/20 hover:bg-white/30 transition-colors text-white text-xs font-medium px-3 py-1.5 rounded-lg"
      @click="emit('retry')"
    >
      Retry
    </button>

    <!-- Dismiss Button -->
    <button
      v-if="showDismiss"
      class="flex-shrink-0 text-white/50 hover:text-white transition-colors p-1"
      aria-label="Dismiss error"
      @click="emit('dismiss')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  message: string;
  showRetry?: boolean;
  showDismiss?: boolean;
}

withDefaults(defineProps<Props>(), {
  showRetry: false,
  showDismiss: true,
});

const emit = defineEmits<{
  (e: 'retry'): void;
  (e: 'dismiss'): void;
}>();
</script>