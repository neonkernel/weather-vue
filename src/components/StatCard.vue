<template>
  <div class="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 flex items-center gap-3 border border-white/10">
    <span class="text-2xl flex-shrink-0" aria-hidden="true">{{ icon }}</span>
    <div class="min-w-0">
      <p class="text-white/50 text-xs font-medium uppercase tracking-wide truncate">{{ label }}</p>
      <p class="text-white font-semibold text-sm mt-0.5 truncate">{{ value }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string
  label: string
  value: string
}>()
</script>