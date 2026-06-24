import { ref } from 'vue'
import { fetchWeatherByCity, fetchWeatherByCoords } from '../services/weatherService'
import type { WeatherData } from '../types/weather'

export function useWeatherApi() {
  const weatherData = ref<WeatherData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByCity(city: string) {
    loading.value = true
    error.value = null
    try {
      weatherData.value = await fetchWeatherByCity(city)
    } catch (err: any) {
      error.value = err?.message || 'Failed to fetch weather data.'
      weatherData.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchByCoords(lat: number, lon: number) {
    loading.value = true
    error.value = null
    try {
      weatherData.value = await fetchWeatherByCoords(lat, lon)
    } catch (err: any) {
      error.value = err?.message || 'Failed to fetch weather data.'
      weatherData.value = null
    } finally {
      loading.value = false
    }
  }

  return { weatherData, loading, error, fetchByCity, fetchByCoords }
}