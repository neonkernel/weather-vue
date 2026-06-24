<template>
  <div class="flex flex-col items-center justify-center gap-1 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
    <span class="text-2xl">{{ icon }}</span>
    <span class="text-lg font-semibold text-white">{{ value }}</span>
    <span class="text-xs text-white/50">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  icon: string
}>()
</script>