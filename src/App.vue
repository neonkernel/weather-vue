<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
      <!-- Header -->
      <header class="mb-8 text-center">
        <h1 class="text-4xl font-bold mb-2 tracking-tight">
          🌤 Weather Dashboard
        </h1>
        <p class="text-blue-200 text-sm">Real-time weather powered by Open-Meteo</p>
      </header>

      <!-- Permission Notice -->
      <PermissionNotice
        v-if="showPermissionNotice"
        :fallback-city="locationStore.cityName"
        @dismiss="showPermissionNotice = false"
      />

      <!-- Search Bar -->
      <SearchBar
        class="mb-6"
        :is-loading="geoLoading"
        @search="handleCitySearch"
        @use-my-location="handleUseMyLocation"
      />

      <!-- Location Status -->
      <LocationStatus
        v-if="locationStore.cityName"
        class="mb-4"
        :city-name="locationStore.cityName"
        :source="locationStore.source"
      />

      <!-- Detecting Location State -->
      <div
        v-if="geoLoading"
        class="flex items-center justify-center gap-3 mb-6 p-4 bg-white/10 rounded-xl backdrop-blur"
      >
        <svg class="animate-spin h-5 w-5 text-blue-300" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span class="text-blue-200 text-sm">Detecting your location...</span>
      </div>

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-if="weatherApi.weatherData.value && !weatherApi.loading.value"
        :weather="weatherApi.weatherData.value"
        :location="weatherApi.currentLocation.value"
      />

      <!-- Loading Spinner -->
      <LoadingSpinner v-else-if="weatherApi.loading.value" message="Fetching weather data..." />

      <!-- Error Message -->
      <ErrorMessage
        v-else-if="weatherApi.error.value && !weatherApi.loading.value"
        :message="weatherApi.error.value"
        @retry="retryLastFetch"
      />

      <!-- Initial State (no data, no loading, no error) -->
      <div
        v-else-if="!weatherApi.weatherData.value && !weatherApi.loading.value && !weatherApi.error.value && !geoLoading"
        class="text-center py-16 text-blue-200"
      >
        <div class="text-6xl mb-4">🌍</div>
        <p class="text-lg font-medium">Search for a city or allow location access</p>
        <p class="text-sm mt-2 opacity-70">to see current weather conditions</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import { reverseGeocode } from './services/weatherService'
import SearchBar from './components/SearchBar.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ErrorMessage from './components/ErrorMessage.vue'

const DEFAULT_CITY = 'New York'

const locationStore = useLocationStore()
const geolocation = useGeolocation()
const weatherApi = useWeatherApi()

const geoLoading = ref(false)
const showPermissionNotice = ref(false)
let lastSearchCity = ref<string | null>(null)

async function handleUseMyLocation() {
  geoLoading.value = true
  showPermissionNotice.value = false

  const coords = await geolocation.getCurrentPosition()

  if (coords) {
    const cityName = await reverseGeocode(coords.latitude, coords.longitude)
    locationStore.setLocation({
      lat: coords.latitude,
      lon: coords.longitude,
      cityName,
      source: 'geo',
    })
    await weatherApi.fetchByCoords(coords.latitude, coords.longitude, cityName)
  } else {
    if (geolocation.permissionDenied.value) {
      showPermissionNotice.value = true
    }
    // Fall back to default city if no previous data
    if (!weatherApi.weatherData.value) {
      await loadDefaultCity()
    }
  }

  geoLoading.value = false
}

async function handleCitySearch(city: string) {
  lastSearchCity.value = city
  showPermissionNotice.value = false
  await weatherApi.fetchByCity(city)
}

async function loadDefaultCity() {
  locationStore.setLocation({
    lat: null,
    lon: null,
    cityName: DEFAULT_CITY,
    source: 'default',
  })
  await weatherApi.fetchByCity(DEFAULT_CITY)
}

async function retryLastFetch() {
  weatherApi.clearError()
  if (locationStore.lat !== null && locationStore.lon !== null) {
    await weatherApi.fetchByCoords(locationStore.lat, locationStore.lon, locationStore.cityName)
  } else if (lastSearchCity.value) {
    await weatherApi.fetchByCity(lastSearchCity.value)
  } else {
    await loadDefaultCity()
  }
}

onMounted(async () => {
  // Auto-detect location on app load
  await handleUseMyLocation()
})
</script>