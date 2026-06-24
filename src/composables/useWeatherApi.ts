import { ref } from 'vue'
import { fetchWeatherByCoords, type WeatherData } from '../services/weatherService'
import { searchCity } from '../services/geocodingService'

export function useWeatherApi() {
  const weatherData = ref<WeatherData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByCoords(lat: number, lon: number): Promise<WeatherData | null> {
    loading.value = true
    error.value = null

    try {
      const data = await fetchWeatherByCoords(lat, lon)
      weatherData.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data'
      weatherData.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchByCity(cityName: string): Promise<WeatherData | null> {
    loading.value = true
    error.value = null

    try {
      const results = await searchCity(cityName)

      if (!results.length) {
        throw new Error(`No results found for "${cityName}"`)
      }

      const { latitude, longitude } = results[0]
      const data = await fetchWeatherByCoords(latitude, longitude)
      weatherData.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weather data'
      weatherData.value = null
      return null
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
    fetchByCoords,
    fetchByCity,
    clearError,
  }
}