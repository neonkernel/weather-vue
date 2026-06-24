<template>
  <div class="flex flex-col gap-1 rounded-xl bg-white/5 border border-white/10 px-4 py-3">
    <div class="flex items-center gap-1.5">
      <span class="text-base">{{ icon }}</span>
      <span class="text-xs text-slate-400 font-medium uppercase tracking-wide">{{ label }}</span>
    </div>
    <p class="text-lg font-semibold text-white">{{ value }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  icon: string
}>()
</script>