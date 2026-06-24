<template>
  <div class="flex flex-col items-center justify-center rounded-2xl border border-red-400/30 bg-red-500/10 py-12 text-center backdrop-blur-sm">
    <div class="mb-3 text-4xl">⚠️</div>
    <h3 class="mb-1 text-lg font-semibold text-red-300">Something went wrong</h3>
    <p class="mb-4 max-w-sm text-sm text-red-300/70">{{ message }}</p>
    <button
      v-if="$attrs.onRetry"
      class="rounded-lg border border-red-400/40 bg-red-500/20 px-4 py-2 text-sm text-red-300 transition-colors hover:bg-red-500/30"
      @click="$emit('retry')"
    >
      Try Again
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
}>()

defineEmits<{
  retry: []
}>()
</script>