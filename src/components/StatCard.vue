<template>
  <div class="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl px-4 py-3 flex items-center gap-3">
    <span class="text-2xl select-none" aria-hidden="true">{{ icon }}</span>
    <div class="min-w-0">
      <div class="text-white/60 text-xs uppercase tracking-wider truncate">{{ label }}</div>
      <div class="text-white font-semibold text-sm sm:text-base truncate">{{ value }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string;
  label: string;
  value: string;
}>();
</script>