<template>
  <div
    class="flex items-start gap-3 bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm shadow-sm"
    role="alert"
  >
    <span class="text-lg leading-none mt-0.5" aria-hidden="true">⚠️</span>
    <div>
      <p class="font-semibold">Error</p>
      <p class="text-red-700 mt-0.5">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>