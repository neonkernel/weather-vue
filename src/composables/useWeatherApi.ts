import { ref } from 'vue'
import type { Ref } from 'vue'
import type { WeatherData } from '../types/weather'
import { geocodeCity } from '../services/geocodingService'
import { getWeatherForLocation } from '../services/weatherService'

export interface UseWeatherApiReturn {
  data: Ref<WeatherData | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  fetchByCity: (cityName: string) => Promise<void>
  reset: () => void
}

export function useWeatherApi(): UseWeatherApiReturn {
  const data = ref<WeatherData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchByCity(cityName: string): Promise<void> {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name to search.'
      return
    }

    loading.value = true
    error.value = null

    try {
      // Step 1: Geocode the city name to lat/lon
      const location = await geocodeCity(cityName)

      // Step 2: Fetch weather data using the coordinates
      const weatherData = await getWeatherForLocation(location)

      data.value = weatherData
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred.'
      error.value = message
      // Keep previous data visible if available? Clear it for a cleaner UX on new search.
      data.value = null
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    data.value = null
    loading.value = false
    error.value = null
  }

  return { data, loading, error, fetchByCity, reset }
}