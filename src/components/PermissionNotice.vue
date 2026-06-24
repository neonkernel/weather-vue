<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    enter-from-class="opacity-0 -translate-y-2"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition-all duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 -translate-y-2"
  >
    <div
      v-if="visible"
      class="flex items-start gap-3 px-4 py-3 rounded-xl border border-amber-400/30 bg-amber-500/10 backdrop-blur-sm"
      role="alert"
    >
      <!-- Icon -->
      <div class="flex-shrink-0 mt-0.5">
        <svg
          class="w-5 h-5 text-amber-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>

      <!-- Message -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-amber-300">Location Access Denied</p>
        <p class="mt-0.5 text-xs text-amber-200/70">
          We couldn't access your location. Showing weather for
          <span class="font-semibold text-amber-200">{{ fallbackCity }}</span> instead.
          You can search for any city using the search bar above.
        </p>
      </div>

      <!-- Dismiss button -->
      <button
        @click="dismiss"
        class="flex-shrink-0 p-1 rounded-lg text-amber-400/60 hover:text-amber-300 hover:bg-amber-400/10 transition-colors duration-150"
        aria-label="Dismiss notice"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  fallbackCity: string
}>()

const emit = defineEmits<{
  dismissed: []
}>()

const visible = ref(true)

function dismiss() {
  visible.value = false
  emit('dismissed')
}
</script>