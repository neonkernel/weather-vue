<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-sky-50 to-indigo-100">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <!-- Header -->
      <header class="mb-8 text-center">
        <h1 class="text-3xl font-bold text-gray-800 mb-1">
          🌤 Weather Dashboard
        </h1>
        <p class="text-gray-500 text-sm">Real-time weather information</p>
      </header>

      <!-- Search Bar -->
      <div class="mb-4">
        <SearchBar
          :loading="weatherLoading"
          :geo-loading="geoLoading"
          @search="handleCitySearch"
          @use-location="handleUseMyLocation"
        />
      </div>

      <!-- Detecting location state -->
      <div v-if="detectingLocation" class="mb-4 flex items-center gap-2 text-blue-600 text-sm">
        <span class="animate-spin">⏳</span>
        <span>Detecting your location...</span>
      </div>

      <!-- Location Status -->
      <div class="mb-4">
        <LocationStatus
          v-if="locationStore.cityName"
          :city-name="locationStore.cityName"
          :source="locationStore.source"
        />
      </div>

      <!-- Permission Notice -->
      <div class="mb-4">
        <PermissionNotice
          v-if="showPermissionNotice"
          :fallback-city="DEFAULT_CITY"
        />
      </div>

      <!-- Error Message -->
      <div v-if="weatherError" class="mb-4">
        <ErrorMessage :message="weatherError" />
      </div>

      <!-- Loading Spinner -->
      <div v-if="weatherLoading" class="flex justify-center py-16">
        <LoadingSpinner />
      </div>

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-else-if="weatherData"
        :weather-data="weatherData"
      />

      <!-- Empty state -->
      <div
        v-else-if="!weatherLoading && !weatherError"
        class="text-center py-16 text-gray-400"
      >
        <div class="text-6xl mb-4">🌍</div>
        <p class="text-lg font-medium">No weather data yet</p>
        <p class="text-sm mt-1">Search for a city or allow location access</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import { fetchWeatherByCoords } from './services/weatherService'

import SearchBar from './components/SearchBar.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'
import ErrorMessage from './components/ErrorMessage.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

const locationStore = useLocationStore()
const { detectLocation, loading: geoLoading, permissionDenied } = useGeolocation()
const { weatherData, loading: weatherLoading, error: weatherError, fetchByCoords, fetchByCity } = useWeatherApi()

const detectingLocation = ref(false)
const showPermissionNotice = ref(false)

async function handleUseMyLocation() {
  detectingLocation.value = true
  showPermissionNotice.value = false

  const coords = await detectLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.lat,
      lon: coords.lon,
      cityName: 'Your Location',
      source: 'geo',
    })
    await fetchByCoords(coords.lat, coords.lon)

    // Update city name from fetched data if available
    if (weatherData.value?.city) {
      locationStore.setLocation({
        lat: coords.lat,
        lon: coords.lon,
        cityName: weatherData.value.city,
        source: 'geo',
      })
    }
  } else {
    // Geolocation failed – fall back to default
    showPermissionNotice.value = permissionDenied.value
    await fallbackToDefault()
  }

  detectingLocation.value = false
}

async function handleCitySearch(city: string) {
  showPermissionNotice.value = false
  await fetchByCity(city)

  if (weatherData.value) {
    locationStore.setLocation({
      lat: weatherData.value.lat,
      lon: weatherData.value.lon,
      cityName: weatherData.value.city,
      source: 'search',
    })
  }
}

async function fallbackToDefault() {
  locationStore.setDefault(DEFAULT_CITY, DEFAULT_LAT, DEFAULT_LON)
  await fetchByCoords(DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY)
}

onMounted(async () => {
  detectingLocation.value = true

  const coords = await detectLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.lat,
      lon: coords.lon,
      cityName: 'Your Location',
      source: 'geo',
    })
    await fetchByCoords(coords.lat, coords.lon)

    // Update city name from fetched data
    if (weatherData.value?.city) {
      locationStore.setLocation({
        lat: coords.lat,
        lon: coords.lon,
        cityName: weatherData.value.city,
        source: 'geo',
      })
    }
  } else {
    if (permissionDenied.value) {
      showPermissionNotice.value = true
    }
    await fallbackToDefault()
  }

  detectingLocation.value = false
})
</script>