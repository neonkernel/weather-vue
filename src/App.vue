<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
      <!-- Header -->
      <div class="mb-8 text-center">
        <h1 class="text-3xl font-bold text-white mb-1">Weather Dashboard</h1>
        <p class="text-gray-400 text-sm">Real-time weather at your fingertips</p>
      </div>

      <!-- Search Bar -->
      <div class="mb-4">
        <SearchBar
          :is-loading="weatherLoading"
          :geo-loading="geoLoading"
          @search="handleSearch"
          @geolocate="handleGeolocate"
        />
      </div>

      <!-- Permission Notice -->
      <div class="mb-4" v-if="showPermissionNotice">
        <PermissionNotice :fallback-city="locationStore.cityName" />
      </div>

      <!-- Location Status -->
      <div class="mb-6 flex justify-center" v-if="locationStore.cityName">
        <LocationStatus
          :city-name="locationStore.cityName"
          :source="locationStore.source"
        />
      </div>

      <!-- Geo detecting state -->
      <div v-if="geoLoading && !weatherLoading" class="text-center py-12">
        <div class="inline-flex flex-col items-center gap-3 text-gray-300">
          <div class="w-10 h-10 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          <span class="text-sm">Detecting your location...</span>
        </div>
      </div>

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-else
        :current-weather="currentWeather"
        :forecast="forecast"
        :loading="weatherLoading"
        :error="weatherError"
        :city-name="locationStore.cityName"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLocationStore } from './stores/locationStore'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import { useGeocoding } from './composables/useGeocoding'

import SearchBar from './components/SearchBar.vue'
import WeatherDashboard from './components/WeatherDashboard.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'

const locationStore = useLocationStore()
const { detectLocation, loading: geoLoading, permissionDenied } = useGeolocation()
const { currentWeather, forecast, loading: weatherLoading, error: weatherError, fetchByCoords, fetchByCity } = useWeatherApi()
const { reverseGeocode } = useGeocoding()

const showPermissionNotice = ref(false)

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

async function handleGeolocate() {
  showPermissionNotice.value = false
  const coords = await detectLocation()

  if (coords) {
    // Try to get a human-readable city name from coordinates
    let cityName = 'Your Location'
    try {
      const geocoded = await reverseGeocode(coords.latitude, coords.longitude)
      if (geocoded) cityName = geocoded
    } catch {
      // Ignore reverse geocoding failures
    }

    locationStore.setLocation({
      lat: coords.latitude,
      lon: coords.longitude,
      cityName,
      source: 'geo',
    })

    await fetchByCoords(coords.latitude, coords.longitude)
  } else {
    // Permission denied or error — fall back to default
    showPermissionNotice.value = permissionDenied.value
    locationStore.setDefaultLocation()
    await fetchByCoords(DEFAULT_LAT, DEFAULT_LON)
  }
}

async function handleSearch(query: string) {
  showPermissionNotice.value = false
  try {
    locationStore.setLocation({
      lat: locationStore.lat ?? 0,
      lon: locationStore.lon ?? 0,
      cityName: query,
      source: 'search',
    })
    await fetchByCity(query)
    // Update lat/lon from successful fetch if needed
    locationStore.setCityName(query)
  } catch {
    // weatherError will be set by useWeatherApi
  }
}

onMounted(async () => {
  await handleGeolocate()
})
</script>