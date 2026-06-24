<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
      <!-- Header -->
      <header class="mb-8 text-center">
        <h1 class="text-4xl font-bold text-white mb-1">
          ⛅ Weather Dashboard
        </h1>
        <p class="text-blue-300/70 text-sm">Real-time weather at your fingertips</p>
      </header>

      <!-- Search Bar -->
      <div class="mb-4">
        <SearchBar
          :geo-loading="geoLoading"
          @search="handleSearch"
          @geolocate="handleGeolocate"
        />
      </div>

      <!-- Location Status -->
      <div class="flex items-center justify-between mb-4">
        <LocationStatus />
        <span v-if="weatherApi.loading.value" class="text-xs text-blue-300/60 animate-pulse">
          Updating...
        </span>
      </div>

      <!-- Permission Notice -->
      <div class="mb-4" v-if="showPermissionNotice">
        <PermissionNotice :fallback-city="defaultCity" />
      </div>

      <!-- Detecting Location State -->
      <div
        v-if="detectingLocation"
        class="flex items-center justify-center gap-3 py-16 text-blue-300"
      >
        <svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span class="text-lg">Detecting your location...</span>
      </div>

      <!-- Main Content -->
      <template v-else>
        <LoadingSpinner v-if="weatherApi.loading.value" />

        <ErrorMessage
          v-else-if="weatherApi.error.value"
          :message="weatherApi.error.value"
        />

        <WeatherDashboard
          v-else-if="weatherApi.weatherData.value"
          :weather="weatherApi.weatherData.value"
        />

        <div
          v-else
          class="flex flex-col items-center justify-center py-24 text-center"
        >
          <span class="text-6xl mb-4">🌤️</span>
          <p class="text-gray-400 text-lg">Search for a city to see the weather</p>
          <p class="text-gray-500 text-sm mt-1">Or allow location access for automatic detection</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import SearchBar from './components/SearchBar.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ErrorMessage from './components/ErrorMessage.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'

const DEFAULT_CITY = 'New York'
const defaultCity = DEFAULT_CITY

const locationStore = useLocationStore()
const geolocation = useGeolocation()
const weatherApi = useWeatherApi()

const detectingLocation = ref(false)
const showPermissionNotice = ref(false)
const geoLoading = ref(false)

async function handleGeolocate() {
  geoLoading.value = true
  showPermissionNotice.value = false

  const coords = await geolocation.detectLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.latitude,
      lon: coords.longitude,
      cityName: 'Current Location',
      source: 'geo',
    })
    await weatherApi.fetchByCoords(coords.latitude, coords.longitude)

    // Update city name from the resolved weather data
    if (weatherApi.weatherData.value?.city) {
      locationStore.setLocation({
        lat: coords.latitude,
        lon: coords.longitude,
        cityName: weatherApi.weatherData.value.city,
        source: 'geo',
      })
    }
  } else {
    if (geolocation.permissionDenied.value) {
      showPermissionNotice.value = true
    }
    // Fall back to default city if not already showing something
    if (!weatherApi.weatherData.value) {
      await loadDefaultCity()
    }
  }

  geoLoading.value = false
}

async function handleSearch(city: string) {
  showPermissionNotice.value = false
  locationStore.setLocation({
    lat: null,
    lon: null,
    cityName: city,
    source: 'search',
  })
  await weatherApi.fetchByCity(city)

  // Update city name from resolved data
  if (weatherApi.weatherData.value?.city) {
    locationStore.setLocation({
      lat: null,
      lon: null,
      cityName: weatherApi.weatherData.value.city,
      source: 'search',
    })
  }
}

async function loadDefaultCity() {
  locationStore.setLocation({
    lat: null,
    lon: null,
    cityName: DEFAULT_CITY,
    source: 'default',
  })
  await weatherApi.fetchByCity(DEFAULT_CITY)
  if (weatherApi.weatherData.value?.city) {
    locationStore.setLocation({
      lat: null,
      lon: null,
      cityName: weatherApi.weatherData.value.city,
      source: 'default',
    })
  }
}

onMounted(async () => {
  detectingLocation.value = true

  const coords = await geolocation.detectLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.latitude,
      lon: coords.longitude,
      cityName: 'Current Location',
      source: 'geo',
    })
    await weatherApi.fetchByCoords(coords.latitude, coords.longitude)

    if (weatherApi.weatherData.value?.city) {
      locationStore.setLocation({
        lat: coords.latitude,
        lon: coords.longitude,
        cityName: weatherApi.weatherData.value.city,
        source: 'geo',
      })
    }
  } else {
    if (geolocation.permissionDenied.value) {
      showPermissionNotice.value = true
    }
    await loadDefaultCity()
  }

  detectingLocation.value = false
})
</script>