<template>
  <div class="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/10">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-base" aria-hidden="true">{{ icon }}</span>
      <span class="text-xs text-white/60 font-medium uppercase tracking-wide">{{ label }}</span>
    </div>
    <div class="text-white font-semibold text-lg">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon: string;
  label: string;
  value: string | number;
}

defineProps<Props>();
</script>