<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 p-4 sm:p-8">
    <div class="max-w-3xl mx-auto space-y-6">

      <!-- Header -->
      <header class="text-center pt-4 pb-2">
        <h1 class="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-1">
          🌤️ Weather Dashboard
        </h1>
        <p class="text-white/60 text-sm">Powered by Open-Meteo — no API key required</p>
      </header>

      <!-- Search Bar -->
      <SearchBar :loading="loading" @search="onSearch" />

      <!-- Loading State -->
      <LoadingSpinner
        v-if="loading"
        message="Fetching weather data…"
        sub-message="Looking up your city and retrieving conditions."
      />

      <!-- Error State -->
      <ErrorMessage
        v-else-if="error"
        :message="error"
        title="Failed to load weather"
        :show-retry="!!lastQuery"
        @retry="onRetry"
      />

      <!-- Empty / Welcome State -->
      <div
        v-else-if="!data"
        class="text-center py-16 text-white/50"
      >
        <div class="text-6xl mb-4 select-none">🌍</div>
        <p class="text-lg font-light">Search for a city to see current weather and forecast.</p>
        <p class="text-sm mt-2">Try "London", "Tokyo", or "New York"</p>
      </div>

      <!-- Weather Data -->
      <template v-else>
        <!-- Current Weather -->
        <div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 shadow-xl">
          <CurrentWeather
            :weather="data.current"
            :location="data.location"
          />
        </div>

        <!-- Forecast Strip -->
        <div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 shadow-xl">
          <ForecastStrip :forecast="data.forecast" />
        </div>

        <!-- Last updated -->
        <p class="text-center text-white/40 text-xs">
          Last updated: {{ lastUpdated }}
        </p>
      </template>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import SearchBar from './SearchBar.vue';
import CurrentWeather from './CurrentWeather.vue';
import ForecastStrip from './ForecastStrip.vue';
import LoadingSpinner from './LoadingSpinner.vue';
import ErrorMessage from './ErrorMessage.vue';
import { useWeatherApi } from '../composables/useWeatherApi';

const { data, loading, error, fetchByCity } = useWeatherApi();
const lastQuery = ref('');

async function onSearch(city: string) {
  lastQuery.value = city;
  await fetchByCity(city);
}

function onRetry() {
  if (lastQuery.value) {
    fetchByCity(lastQuery.value);
  }
}

const lastUpdated = computed(() => {
  if (!data.value?.fetchedAt) return '';
  return data.value.fetchedAt.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
});
</script>