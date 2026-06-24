import { ref } from 'vue'
import {
  fetchWeatherByCoords,
  fetchWeatherByCity,
  reverseGeocode,
  type WeatherData,
  type GeocodingResult,
} from '../services/weatherService'
import { useLocationStore } from '../stores/locationStore'

export function useWeatherApi() {
  const weatherData = ref<WeatherData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentLocation = ref<GeocodingResult | null>(null)

  const locationStore = useLocationStore()

  async function fetchByCoords(lat: number, lon: number, cityName?: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const weather = await fetchWeatherByCoords(lat, lon)
      weatherData.value = weather

      // If no city name provided, attempt reverse geocoding
      const resolvedCityName = cityName || (await reverseGeocode(lat, lon))

      currentLocation.value = {
        id: 0,
        name: resolvedCityName,
        latitude: lat,
        longitude: lon,
        country: '',
      }
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data.'
      weatherData.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchByCity(city: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const { weather, location } = await fetchWeatherByCity(city)
      weatherData.value = weather
      currentLocation.value = location

      locationStore.setLocation({
        lat: location.latitude,
        lon: location.longitude,
        cityName: location.name,
        source: 'search',
      })
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data.'
      weatherData.value = null
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    weatherData,
    loading,
    error,
    currentLocation,
    fetchByCoords,
    fetchByCity,
    clearError,
  }
}