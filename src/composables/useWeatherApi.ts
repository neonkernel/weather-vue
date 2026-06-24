import { ref } from 'vue'
import { weatherService, type WeatherServiceResult } from '../services/weatherService'

export function useWeatherApi() {
  const weatherData = ref<WeatherServiceResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByCity(city: string) {
    loading.value = true
    error.value = null
    try {
      weatherData.value = await weatherService.fetchByCity(city)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data'
      weatherData.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchByCoords(lat: number, lon: number) {
    loading.value = true
    error.value = null
    try {
      weatherData.value = await weatherService.fetchByCoords(lat, lon)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data'
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
    fetchByCity,
    fetchByCoords,
    clearError,
  }
}