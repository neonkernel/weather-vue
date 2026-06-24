<template>
  <div class="flex flex-col items-center justify-center py-12 gap-4">
    <div class="text-5xl">⛈️</div>
    <div class="text-center">
      <p class="text-lg font-medium text-red-300 mb-1">Something went wrong</p>
      <p class="text-sm text-blue-200 max-w-md">{{ message }}</p>
    </div>
    <button
      v-if="showRetry"
      type="button"
      class="px-6 py-2 rounded-xl bg-blue-500 hover:bg-blue-400 text-white text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-400"
      @click="$emit('retry')"
    >
      Try Again
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
  showRetry?: boolean
}>()

withDefaults(defineProps<{
  message: string
  showRetry?: boolean
}>(), {
  showRetry: true,
})

defineEmits<{
  retry: []
}>()
</script>