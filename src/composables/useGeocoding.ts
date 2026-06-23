import { ref } from 'vue'
import type { Ref } from 'vue'
import type { GeocodingResult } from '../types/weather'
import { geocodeCity } from '../services/geocodingService'

export interface UseGeocodingReturn {
  result: Ref<GeocodingResult | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  geocode: (cityName: string) => Promise<GeocodingResult | null>
  reset: () => void
}

export function useGeocoding(): UseGeocodingReturn {
  const result = ref<GeocodingResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function geocode(cityName: string): Promise<GeocodingResult | null> {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name.'
      return null
    }

    loading.value = true
    error.value = null
    result.value = null

    try {
      const location = await geocodeCity(cityName)
      result.value = location
      return location
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to find city location.'
      error.value = message
      return null
    } finally {
      loading.value = false
    }
  }

  function reset() {
    result.value = null
    loading.value = false
    error.value = null
  }

  return { result, loading, error, geocode, reset }
}