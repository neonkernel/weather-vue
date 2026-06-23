<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 p-4 sm:p-6 lg:p-8">
    <div class="max-w-2xl mx-auto">

      <!-- Header -->
      <header class="text-center mb-8">
        <h1 class="text-3xl font-bold text-white mb-1 tracking-tight">
          🌤️ Weather Dashboard
        </h1>
        <p class="text-white/50 text-sm">Live weather data powered by Open-Meteo</p>
      </header>

      <!-- Search Bar -->
      <div class="mb-8">
        <SearchBar :loading="loading" @search="handleSearch" />
      </div>

      <!-- Initial state: no search yet -->
      <div
        v-if="!data && !loading && !error"
        class="text-center py-16"
      >
        <div class="text-6xl mb-4">🗺️</div>
        <h2 class="text-white text-xl font-semibold mb-2">Search for a City</h2>
        <p class="text-white/50 text-sm max-w-xs mx-auto">
          Enter a city name above to get current weather conditions and a 7-day forecast.
        </p>
        <div class="mt-6 flex flex-wrap gap-2 justify-center">
          <button
            v-for="suggestion in suggestedCities"
            :key="suggestion"
            @click="handleSearch(suggestion)"
            class="
              px-3 py-1.5 rounded-full text-sm
              bg-white/10 hover:bg-white/20
              text-white/70 hover:text-white
              border border-white/10
              transition-all duration-150
            "
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <!-- Loading state -->
      <LoadingSpinner
        v-else-if="loading"
        :message="`Fetching weather for ${lastSearchedCity}...`"
        sub-message="Contacting Open-Meteo API"
      />

      <!-- Error state -->
      <ErrorMessage
        v-else-if="error"
        :message="error"
        title="Failed to load weather"
        :show-retry="!!lastSearchedCity"
        @retry="handleRetry"
      />

      <!-- Weather data -->
      <template v-else-if="data">
        <div class="space-y-6">
          <!-- Current weather card -->
          <div class="bg-white/10 backdrop-blur-sm rounded-3xl p-6 border border-white/20 shadow-xl">
            <CurrentWeather
              :weather="data.current"
              :city="data.city"
              :country="data.country"
              :last-updated="data.lastUpdated"
            />
          </div>

          <!-- 7-day forecast -->
          <div class="bg-white/10 backdrop-blur-sm rounded-3xl p-6 border border-white/20 shadow-xl">
            <ForecastStrip :forecast="data.forecast" />
          </div>

          <!-- Additional details -->
          <div class="bg-white/5 rounded-2xl p-4 border border-white/10">
            <p class="text-white/30 text-xs text-center">
              Data provided by
              <a
                href="https://open-meteo.com/"
                target="_blank"
                rel="noopener noreferrer"
                class="text-white/50 hover:text-white underline transition-colors"
              >
                Open-Meteo
              </a>
              · Free & No API Key Required
            </p>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SearchBar from './SearchBar.vue'
import CurrentWeather from './CurrentWeather.vue'
import ForecastStrip from './ForecastStrip.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorMessage from './ErrorMessage.vue'
import { useWeatherApi } from '../composables/useWeatherApi'

const { data, loading, error, fetchByCity } = useWeatherApi()

const lastSearchedCity = ref('')

const suggestedCities = ['New York', 'London', 'Tokyo', 'Paris', 'Sydney', 'Dubai']

async function handleSearch(cityName: string) {
  lastSearchedCity.value = cityName
  await fetchByCity(cityName)
}

function handleRetry() {
  if (lastSearchedCity.value) {
    handleSearch(lastSearchedCity.value)
  }
}
</script>