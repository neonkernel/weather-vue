<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useGeolocation } from './composables/useGeolocation'
import { useWeatherApi } from './composables/useWeatherApi'
import { useLocationStore } from './stores/locationStore'
import WeatherDashboard from './components/WeatherDashboard.vue'
import SearchBar from './components/SearchBar.vue'
import LoadingSpinner from './components/LoadingSpinner.vue'
import ErrorMessage from './components/ErrorMessage.vue'
import LocationStatus from './components/LocationStatus.vue'
import PermissionNotice from './components/PermissionNotice.vue'

const DEFAULT_CITY = 'New York'
const DEFAULT_LAT = 40.7128
const DEFAULT_LON = -74.006

const locationStore = useLocationStore()
const { getCurrentLocation, loading: geoLoading, permissionDenied } = useGeolocation()
const {
  currentWeather,
  forecast,
  loading: weatherLoading,
  error: weatherError,
  resolvedCityName,
  fetchByCoords,
  fetchByCity,
} = useWeatherApi()

const detectingLocation = ref(false)
const showPermissionNotice = ref(false)
const initializationDone = ref(false)

async function initializeWithGeolocation() {
  detectingLocation.value = true
  const coords = await getCurrentLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.lat,
      lon: coords.lon,
      cityName: 'Your Location',
      source: 'geo',
    })
    await fetchByCoords(coords.lat, coords.lon)
    if (resolvedCityName.value) {
      locationStore.setCityName(resolvedCityName.value)
    }
  } else {
    // Fallback to default city
    if (permissionDenied.value) {
      showPermissionNotice.value = true
    }
    locationStore.setLocation({
      lat: DEFAULT_LAT,
      lon: DEFAULT_LON,
      cityName: DEFAULT_CITY,
      source: 'default',
    })
    await fetchByCity(DEFAULT_CITY)
    if (resolvedCityName.value) {
      locationStore.setCityName(resolvedCityName.value)
    }
  }

  detectingLocation.value = false
  initializationDone.value = true
}

async function handleSearch(city: string) {
  await fetchByCity(city)
  if (resolvedCityName.value) {
    locationStore.setLocation({
      lat: null,
      lon: null,
      cityName: resolvedCityName.value,
      source: 'search',
    })
  } else {
    locationStore.setLocation({
      lat: null,
      lon: null,
      cityName: city,
      source: 'search',
    })
  }
  showPermissionNotice.value = false
}

async function handleUseMyLocation() {
  detectingLocation.value = true
  showPermissionNotice.value = false
  const coords = await getCurrentLocation()

  if (coords) {
    locationStore.setLocation({
      lat: coords.lat,
      lon: coords.lon,
      cityName: 'Your Location',
      source: 'geo',
    })
    await fetchByCoords(coords.lat, coords.lon)
    if (resolvedCityName.value) {
      locationStore.setCityName(resolvedCityName.value)
    }
  } else {
    if (permissionDenied.value) {
      showPermissionNotice.value = true
    }
  }

  detectingLocation.value = false
}

function dismissPermissionNotice() {
  showPermissionNotice.value = false
}

onMounted(() => {
  initializeWithGeolocation()
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
    <div class="container mx-auto px-4 py-8 max-w-5xl">
      <!-- Header -->
      <header class="mb-8">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 class="text-3xl font-bold text-white tracking-tight">
              ☁️ Weather Dashboard
            </h1>
            <p class="text-slate-400 text-sm mt-1">
              Real-time weather powered by Open-Meteo
            </p>
          </div>
          <LocationStatus
            :city-name="locationStore.cityName"
            :source="locationStore.source"
            :loading="detectingLocation"
          />
        </div>
      </header>

      <!-- Permission Notice -->
      <PermissionNotice
        v-if="showPermissionNotice"
        :fallback-city="locationStore.cityName"
        @dismiss="dismissPermissionNotice"
      />

      <!-- Search Bar -->
      <SearchBar
        class="mb-6"
        :detecting-location="detectingLocation"
        @search="handleSearch"
        @use-my-location="handleUseMyLocation"
      />

      <!-- Detecting Location State -->
      <div
        v-if="detectingLocation && !initializationDone"
        class="flex flex-col items-center justify-center py-20 gap-4"
      >
        <LoadingSpinner size="lg" />
        <p class="text-slate-300 text-lg animate-pulse">Detecting your location...</p>
        <p class="text-slate-500 text-sm">Please allow location access when prompted</p>
      </div>

      <!-- Weather Loading -->
      <div
        v-else-if="weatherLoading"
        class="flex flex-col items-center justify-center py-20 gap-4"
      >
        <LoadingSpinner size="lg" />
        <p class="text-slate-300 text-lg animate-pulse">Loading weather data...</p>
      </div>

      <!-- Error State -->
      <ErrorMessage
        v-else-if="weatherError"
        :message="weatherError"
        class="mt-4"
      />

      <!-- Weather Dashboard -->
      <WeatherDashboard
        v-else-if="currentWeather && initializationDone"
        :current-weather="currentWeather"
        :forecast="forecast"
        :city-name="locationStore.cityName"
      />
    </div>
  </div>
</template>