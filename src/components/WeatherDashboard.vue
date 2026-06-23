<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white px-4 py-8">
    <div class="max-w-2xl mx-auto flex flex-col gap-6">

      <!-- Header -->
      <header class="text-center">
        <h1 class="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-1">
          🌤️ Weather Dashboard
        </h1>
        <p class="text-slate-400 text-sm">Enter a city to get live weather conditions</p>
      </header>

      <!-- Search -->
      <SearchBar
        :loading="loading"
        @search="handleSearch"
      />

      <!-- Error -->
      <Transition name="fade">
        <ErrorMessage
          v-if="error"
          :message="error"
          title="Could not load weather"
          :show-retry="!!lastCity"
          @retry="handleRetry"
        />
      </Transition>

      <!-- Loading -->
      <Transition name="fade">
        <LoadingSpinner v-if="loading" message="Fetching weather data…" />
      </Transition>

      <!-- Weather data -->
      <Transition name="slide-up">
        <div v-if="data && !loading" class="flex flex-col gap-4">
          <!-- Current conditions -->
          <CurrentWeather
            :weather="data.current"
            :location-name="data.location.displayName"
          />

          <!-- Forecast strip -->
          <ForecastStrip :forecast="data.forecast" />

          <!-- Last updated -->
          <p class="text-center text-slate-500 text-xs">
            Last updated: {{ formattedFetchTime }}
          </p>
        </div>
      </Transition>

      <!-- Empty state -->
      <Transition name="fade">
        <div
          v-if="!data && !loading && !error"
          class="text-center py-16 text-slate-500 flex flex-col items-center gap-3"
        >
          <span class="text-5xl" aria-hidden="true">🔍</span>
          <p class="text-lg font-light">Search for a city to see the weather</p>
          <p class="text-sm">Try "London", "Tokyo", or "New York"</p>
        </div>
      </Transition>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useWeatherApi } from '../composables/useWeatherApi';
import SearchBar from './SearchBar.vue';
import ErrorMessage from './ErrorMessage.vue';
import LoadingSpinner from './LoadingSpinner.vue';
import CurrentWeather from './CurrentWeather.vue';
import ForecastStrip from './ForecastStrip.vue';

const { data, loading, error, fetchByCity } = useWeatherApi();
const lastCity = ref('');

async function handleSearch(city: string) {
  lastCity.value = city;
  await fetchByCity(city);
}

async function handleRetry() {
  if (lastCity.value) {
    await fetchByCity(lastCity.value);
  }
}

const formattedFetchTime = computed(() => {
  if (!data.value?.fetchedAt) return '';
  return new Date(data.value.fetchedAt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.slide-up-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>