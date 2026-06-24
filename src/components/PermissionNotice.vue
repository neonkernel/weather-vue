<template>
  <Transition name="slide-down">
    <div
      v-if="visible"
      class="relative flex items-start gap-3 rounded-xl border border-amber-400/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200 backdrop-blur-sm"
      role="alert"
    >
      <!-- Icon -->
      <div class="mt-0.5 flex-shrink-0">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 text-amber-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>

      <!-- Message -->
      <div class="flex-1">
        <p class="font-medium text-amber-300">Location access denied</p>
        <p class="mt-0.5 text-amber-200/80">
          We couldn't access your location. Showing weather for
          <strong class="text-amber-200">{{ fallbackCity }}</strong> instead.
          You can search for any city using the search bar above.
        </p>
      </div>

      <!-- Dismiss button -->
      <button
        type="button"
        class="flex-shrink-0 rounded-lg p-1 text-amber-400 transition-colors hover:bg-amber-400/20 hover:text-amber-200 focus:outline-none focus:ring-2 focus:ring-amber-400/50"
        aria-label="Dismiss notification"
        @click="dismiss"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  fallbackCity?: string
  show?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  fallbackCity: 'New York',
  show: true,
})

const emit = defineEmits<{
  dismiss: []
}>()

const visible = ref(props.show)

function dismiss() {
  visible.value = false
  emit('dismiss')
}
</script>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>