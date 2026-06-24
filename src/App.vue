<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 p-4 md:p-8">
    <div class="mx-auto max-w-4xl space-y-4">
      <!-- Header -->
      <header class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white md:text-3xl">
          🌤️ Weather Dashboard
        </h1>
        <LocationStatus />
      </header>

      <!-- Search Bar -->
      <SearchBar
        :geo-loading="geoLoading"
        @city-selected="onCitySelected"
        @geolocate="onGeolocate"
      />

      <!-- Permission Notice (shown when geo was denied) -->
      <PermissionNotice
        v-if="showPermissionNotice"
        :fallback-city="DEFAULT_CITY"
        :show="showPermissionNotice"
        @dismiss="showPermissionNotice = false"
      />

      <!-- Detecting location state -->
      <div
        v-if="geoLoading"
        class="flex items-center gap-3 rounded-xl border border-blue-400/30 bg-blue-500/10 px-4 py-3 text-sm text-blue-300 backdrop-blur-sm"
      >
        <svg
          class="h-5 w-5 animate-spin flex-shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
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
        <span>Detecting your location...</span>
      </div>

      <!-- Main weather dashboard -->
      <WeatherDashboard
        v-if="weatherData || weatherLoading"
        :weather-data="weatherData"
        :loading="weatherLoading"
        :error="weatherError"
      />

      <!-- Error state -->
      <ErrorMessage
        v-else-if="weatherError && !weatherLoading"
        :message="weatherError"
        @retry="retryFetch"
      />

      <!-- Initial empty state (no location yet) -->
      <div
        v-else-if="!geoLoading && !weatherLoading"
        class="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/5 py-20 text-center backdrop-blur-sm"
      >
        <div class="mb-4 text-6xl">🌍</div>
        <h2 class="mb-2 text-xl font-semibold text-white">Welcome to Weather Dashboard</h2>
        <p class="max-w-sm text-sm text-white/60">
          Search for a city or allow location access to see current weather conditions.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import { reverseGeocode } from './services/geocodingService'
import SearchBar from './components/SearchBar.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'
import ErrorMessage from './components/ErrorMessage.vue'

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

const locationStore = useLocationStore()
const { loading: geoLoading, permissionDenied, detect } = useGeolocation()
const { weatherData, loading: weatherLoading, error: weatherError, fetchByCoords } = useWeatherApi()

const showPermissionNotice = ref(false)

async function onGeolocate() {
  showPermissionNotice.value = false
  const coords = await detect()

  if (coords) {
    // Try to resolve city name
    const cityName = await reverseGeocode(coords.lat, coords.lon)
    locationStore.setFromGeo(coords.lat, coords.lon, cityName)
    await fetchByCoords(coords.lat, coords.lon)
  } else if (permissionDenied.value) {
    showPermissionNotice.value = true
    await loadDefaultCity()
  } else {
    // Other error — still load default
    await loadDefaultCity()
  }
}

async function onCitySelected(name: string, lat: number, lon: number) {
  locationStore.setFromSearch(name, lat, lon)
  await fetchByCoords(lat, lon)
}

async function loadDefaultCity() {
  locationStore.setDefault(DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LON)
  await fetchByCoords(DEFAULT_LAT, DEFAULT_LON)
}

async function retryFetch() {
  if (locationStore.hasCoords()) {
    await fetchByCoords(locationStore.lat!, locationStore.lon!)
  } else {
    await loadDefaultCity()
  }
}

onMounted(async () => {
  // Attempt geolocation automatically on load
  const coords = await detect()

  if (coords) {
    const cityName = await reverseGeocode(coords.lat, coords.lon)
    locationStore.setFromGeo(coords.lat, coords.lon, cityName)
    await fetchByCoords(coords.lat, coords.lon)
  } else if (permissionDenied.value) {
    showPermissionNotice.value = true
    await loadDefaultCity()
  } else {
    // Geolocation not supported or other error — use default
    await loadDefaultCity()
  }
})
</script>