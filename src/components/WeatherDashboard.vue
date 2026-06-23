<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-600 p-4 md:p-8">
    <div class="max-w-3xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-white text-2xl font-bold tracking-tight mb-1">
          🌤️ Weather Dashboard
        </h1>
        <p class="text-white/60 text-sm">Powered by Open-Meteo</p>
      </div>

      <!-- Search Bar -->
      <div class="mb-6">
        <SearchBar :loading="loading" @search="handleSearch" />
      </div>

      <!-- Error Message -->
      <div v-if="error" class="mb-6">
        <ErrorMessage
          :message="error"
          :show-retry="!!lastQuery"
          :show-dismiss="true"
          @retry="handleRetry"
          @dismiss="dismissError"
        />
      </div>

      <!-- Loading Spinner -->
      <div v-if="loading" class="mt-8">
        <LoadingSpinner
          title="Fetching weather data..."
          :subtitle="`Looking up weather for ${lastQuery}`"
        />
      </div>

      <!-- Weather Content -->
      <template v-else-if="data && !error">
        <!-- Glassmorphism card -->
        <div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 md:p-8 shadow-2xl">
          <!-- Current Weather -->
          <CurrentWeather
            :weather="data.current"
            :city-name="cityName"
            class="mb-8"
          />

          <!-- Divider -->
          <hr class="border-white/20 mb-6" />

          <!-- Forecast Strip -->
          <ForecastStrip :forecast="data.daily" />
        </div>
      </template>

      <!-- Empty State (initial) -->
      <div
        v-else-if="!loading && !data && !error"
        class="text-center mt-16"
      >
        <div class="text-6xl mb-4">🌍</div>
        <p class="text-white text-xl font-semibold mb-2">Search for a city</p>
        <p class="text-white/60 text-sm">Enter a city name above to see current weather and forecast</p>

        <!-- Quick city suggestions -->
        <div class="flex flex-wrap justify-center gap-2 mt-6">
          <button
            v-for="city in suggestedCities"
            :key="city"
            class="bg-white/10 hover:bg-white/20 border border-white/20 text-white/80 hover:text-white text-sm px-4 py-2 rounded-full transition-all duration-200"
            @click="handleSearch(city)"
          >
            {{ city }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useWeatherApi } from '../composables/useWeatherApi';
import SearchBar from './SearchBar.vue';
import ErrorMessage from './ErrorMessage.vue';
import LoadingSpinner from './LoadingSpinner.vue';
import CurrentWeather from './CurrentWeather.vue';
import ForecastStrip from './ForecastStrip.vue';

const { data, cityName, loading, error, fetchByCity } = useWeatherApi();

const lastQuery = ref('');

const suggestedCities = ['London', 'New York', 'Tokyo', 'Sydney', 'Paris', 'Dubai'];

async function handleSearch(city: string) {
  lastQuery.value = city;
  await fetchByCity(city);
}

function handleRetry() {
  if (lastQuery.value) {
    handleSearch(lastQuery.value);
  }
}

function dismissError() {
  error.value = null;
}
</script>