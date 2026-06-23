<template>
  <div
    class="
      bg-white/5 hover:bg-white/10 transition-colors duration-200
      rounded-2xl px-4 py-3 flex flex-col gap-1
      border border-white/5
    "
  >
    <div class="flex items-center gap-1.5">
      <span class="text-base leading-none" aria-hidden="true">{{ icon }}</span>
      <span class="text-slate-400 text-xs font-medium uppercase tracking-wider">{{ label }}</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-white font-semibold text-lg leading-tight">{{ value }}</span>
      <span
        v-if="badge"
        :class="badgeClasses"
        class="text-xs font-medium px-1.5 py-0.5 rounded-full"
      >
        {{ badge.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  label: string;
  value: string;
  icon?: string;
  badge?: { label: string; color: string };
}>();

const badgeClasses = computed(() => {
  const colorMap: Record<string, string> = {
    green:  'bg-green-500/20 text-green-300',
    yellow: 'bg-yellow-500/20 text-yellow-300',
    orange: 'bg-orange-500/20 text-orange-300',
    red:    'bg-red-500/20 text-red-300',
    purple: 'bg-purple-500/20 text-purple-300',
  };
  return colorMap[props.badge?.color ?? ''] ?? 'bg-white/10 text-white';
});
</script>