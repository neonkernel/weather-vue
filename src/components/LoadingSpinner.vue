<template>
  <div class="flex flex-col items-center gap-3 text-blue-500" role="status" aria-label="Loading">
    <svg
      class="animate-spin w-10 h-10"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
    <span class="text-sm text-gray-500 font-medium">Loading weather data...</span>
  </div>
</template>