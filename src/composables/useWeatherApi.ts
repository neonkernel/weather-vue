import { ref } from 'vue'
import { weatherService } from '../services/weatherService'
import type { WeatherData, ForecastDay } from '../types/weather'

export function useWeatherApi() {
  const currentWeather = ref<WeatherData | null>(null)
  const forecast = ref<ForecastDay[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByCity(cityName: string) {
    loading.value = true
    error.value = null
    try {
      const result = await weatherService.fetchWeatherByCity(cityName)
      currentWeather.value = result.current
      forecast.value = result.forecast
    } catch (err: any) {
      error.value = err?.message || 'Failed to fetch weather data.'
      currentWeather.value = null
      forecast.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchByCoords(lat: number, lon: number) {
    loading.value = true
    error.value = null
    try {
      const result = await weatherService.fetchWeatherByCoords(lat, lon)
      currentWeather.value = result.current
      forecast.value = result.forecast
    } catch (err: any) {
      error.value = err?.message || 'Failed to fetch weather data.'
      currentWeather.value = null
      forecast.value = []
    } finally {
      loading.value = false
    }
  }

  return {
    currentWeather,
    forecast,
    loading,
    error,
    fetchByCity,
    fetchByCoords,
  }
}