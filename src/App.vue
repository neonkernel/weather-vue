<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-5xl">
      <!-- Header -->
      <header class="mb-8">
        <h1 class="text-3xl font-bold text-center mb-2">🌤 Weather Dashboard</h1>
        <p class="text-blue-200 text-center text-sm">Real-time weather powered by Open-Meteo</p>
      </header>

      <!-- Search Bar -->
      <SearchBar
        @search="handleSearch"
        @use-location="handleUseLocation"
        :loading="geoLoading"
        class="mb-4"
      />

      <!-- Permission Notice -->
      <PermissionNotice
        v-if="showPermissionNotice"
        :fallback-city="locationStore.cityName"
        @dismiss="showPermissionNotice = false"
        class="mb-4"
      />

      <!-- Location Status -->
      <LocationStatus
        v-if="locationStore.cityName"
        :city-name="locationStore.cityName"
        :source="locationStore.source"
        class="mb-6"
      />

      <!-- Detecting Location State -->
      <div v-if="geoLoading" class="flex flex-col items-center justify-center py-16">
        <LoadingSpinner />
        <p class="mt-4 text-blue-200 text-lg animate-pulse">Detecting your location...</p>
      </div>

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-else-if="weather"
        :weather="weather"
      />

      <!-- Loading Weather -->
      <div v-else-if="weatherLoading" class="flex flex-col items-center justify-center py-16">
        <LoadingSpinner />
        <p class="mt-4 text-blue-200">Loading weather data...</p>
      </div>

      <!-- Error State -->
      <ErrorMessage
        v-else-if="weatherError"
        :message="weatherError"
        @retry="handleRetry"
      />

      <!-- Initial State -->
      <div v-else class="flex flex-col items-center justify-center py-16 text-blue-200">
        <span class="text-6xl mb-4">🌍</span>
        <p class="text-lg">Enter a city name or allow location access to get started.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import SearchBar from './components/SearchBar.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ErrorMessage from './components/ErrorMessage.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

const locationStore = useLocationStore()
const { loading: geoLoading, permissionDenied, detectLocation } = useGeolocation()
const { weather, loading: weatherLoading, error: weatherError, fetchByCity, fetchByCoords } = useWeatherApi()

const showPermissionNotice = ref(false)
let lastLat: number | null = null
let lastLon: number | null = null

async function handleUseLocation() {
  showPermissionNotice.value = false
  const coords = await detectLocation()

  if (coords) {
    lastLat = coords.latitude
    lastLon = coords.longitude
    await fetchByCoords(coords.latitude, coords.longitude)

    locationStore.setLocation({
      lat: coords.latitude,
      lon: coords.longitude,
      cityName: weather.value?.city || `${coords.latitude.toFixed(2)}, ${coords.longitude.toFixed(2)}`,
      source: 'geo',
    })
  } else if (permissionDenied.value) {
    showPermissionNotice.value = true
    await loadDefault()
  } else {
    await loadDefault()
  }
}

async function handleSearch(city: string) {
  showPermissionNotice.value = false
  await fetchByCity(city)

  if (weather.value) {
    lastLat = weather.value.lat
    lastLon = weather.value.lon
    locationStore.setLocation({
      lat: weather.value.lat,
      lon: weather.value.lon,
      cityName: weather.value.city,
      source: 'search',
    })
  }
}

async function loadDefault() {
  lastLat = DEFAULT_LAT
  lastLon = DEFAULT_LON
  await fetchByCoords(DEFAULT_LAT, DEFAULT_LON)

  locationStore.setLocation({
    lat: DEFAULT_LAT,
    lon: DEFAULT_LON,
    cityName: weather.value?.city || DEFAULT_CITY,
    source: 'default',
  })
}

async function handleRetry() {
  if (lastLat !== null && lastLon !== null) {
    await fetchByCoords(lastLat, lastLon)
  } else if (locationStore.cityName) {
    await fetchByCity(locationStore.cityName)
  } else {
    await loadDefault()
  }
}

onMounted(async () => {
  await handleUseLocation()
})
</script>