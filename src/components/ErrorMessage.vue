<template>
  <div class="flex flex-col items-center justify-center py-12 text-center">
    <span class="text-5xl mb-4">⚡</span>
    <h2 class="text-xl font-semibold text-red-300 mb-2">Something went wrong</h2>
    <p class="text-blue-200 mb-6 max-w-md">{{ message }}</p>
    <button
      v-if="$attrs.onRetry"
      @click="$emit('retry')"
      class="px-6 py-2 bg-blue-500 hover:bg-blue-400 rounded-xl text-white font-medium transition-colors"
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
  (e: 'retry'): void
}>()
</script>