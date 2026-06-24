<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
    <div class="max-w-4xl mx-auto px-4 py-8">
      <!-- Header -->
      <header class="mb-8">
        <h1 class="text-3xl font-bold text-white mb-1">Weather Dashboard</h1>
        <p class="text-slate-400 text-sm">Real-time weather powered by Open-Meteo</p>
      </header>

      <!-- Search Bar -->
      <div class="mb-4">
        <SearchBar
          :is-loading="weatherLoading"
          :geo-loading="geoLoading"
          @search="handleCitySearch"
          @use-location="handleUseLocation"
        />
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
          :fallback-city="locationStore.cityName"
          @dismissed="showPermissionNotice = false"
        />
      </div>

      <!-- Geo detecting state -->
      <div v-if="geoLoading && !weatherLoading" class="mb-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-blue-500/10 border border-blue-400/20">
        <svg class="w-5 h-5 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        <span class="text-sm text-blue-300">Detecting your location...</span>
      </div>

      <!-- Error Message -->
      <div v-if="weatherError" class="mb-6 flex items-start gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-400/20">
        <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
        </svg>
        <div>
          <p class="text-sm font-medium text-red-300">Failed to load weather</p>
          <p class="text-xs text-red-300/70 mt-0.5">{{ weatherError }}</p>
        </div>
      </div>

      <!-- Loading Spinner -->
      <div v-if="weatherLoading" class="flex justify-center items-center py-20">
        <div class="flex flex-col items-center gap-4">
          <svg class="w-10 h-10 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <p class="text-slate-400 text-sm">Loading weather data...</p>
        </div>
      </div>

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-else-if="weatherData"
        :weather="weatherData.current"
        :forecast="weatherData.forecast"
        :city-name="locationStore.cityName"
      />

      <!-- Empty state -->
      <div
        v-else-if="!weatherLoading && !weatherError && !geoLoading"
        class="flex flex-col items-center justify-center py-20 text-center"
      >
        <svg class="w-16 h-16 text-slate-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z"/>
        </svg>
        <p class="text-slate-400 text-lg font-medium">No weather data</p>
        <p class="text-slate-500 text-sm mt-1">Search for a city or use your location to get started</p>
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
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

const locationStore = useLocationStore()
const { loading: geoLoading, permissionDenied, getCurrentPosition } = useGeolocation()
const { weatherData, loading: weatherLoading, error: weatherError, fetchByCoords, fetchByCity } = useWeatherApi()

const showPermissionNotice = ref(false)

async function handleUseLocation() {
  showPermissionNotice.value = false
  const coords = await getCurrentPosition()

  if (coords) {
    locationStore.setCoords(coords.lat, coords.lon, 'My Location', 'geo')
    await fetchByCoords(coords.lat, coords.lon)
  } else {
    // Permission denied or error - fall back to default
    showPermissionNotice.value = true
    locationStore.setCoords(DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY, 'default')
    await fetchByCoords(DEFAULT_LAT, DEFAULT_LON)
  }
}

async function handleCitySearch(city: string) {
  showPermissionNotice.value = false
  locationStore.setCoords(null as any, null as any, city, 'search')
  await fetchByCity(city)
}

onMounted(async () => {
  // Try geolocation on mount
  const coords = await getCurrentPosition()

  if (coords) {
    locationStore.setCoords(coords.lat, coords.lon, 'My Location', 'geo')
    await fetchByCoords(coords.lat, coords.lon)
  } else {
    // Permission denied or unavailable - use default city
    if (permissionDenied.value) {
      showPermissionNotice.value = true
    }
    locationStore.setCoords(DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY, 'default')
    await fetchByCoords(DEFAULT_LAT, DEFAULT_LON)
  }
})
</script>