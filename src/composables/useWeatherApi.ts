import { ref } from 'vue'
import { weatherService } from '../services/weatherService'
import type { WeatherData, ForecastData } from '../types/weather'

export function useWeatherApi() {
  const currentWeather = ref<WeatherData | null>(null)
  const forecast = ref<ForecastData[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const resolvedCityName = ref<string | null>(null)

  async function fetchByCoords(lat: number, lon: number) {
    loading.value = true
    error.value = null
    try {
      const result = await weatherService.fetchByCoords(lat, lon)
      currentWeather.value = result.current
      forecast.value = result.forecast
      resolvedCityName.value = result.cityName ?? null
    } catch (err: any) {
      error.value = err?.message ?? 'Failed to fetch weather data.'
      currentWeather.value = null
      forecast.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchByCity(city: string) {
    loading.value = true
    error.value = null
    try {
      const result = await weatherService.fetchByCity(city)
      currentWeather.value = result.current
      forecast.value = result.forecast
      resolvedCityName.value = result.cityName ?? city
    } catch (err: any) {
      error.value = err?.message ?? 'Failed to fetch weather data.'
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
    resolvedCityName,
    fetchByCoords,
    fetchByCity,
  }
}