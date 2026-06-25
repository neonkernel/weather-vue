import { ref } from 'vue'

export interface GeocodingResult {
  name: string
  country: string
  latitude: number
  longitude: number
  admin1?: string
}

export function useGeocoding() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function geocodeCity(cityName: string): Promise<GeocodingResult | null> {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams({
        name: cityName,
        count: '1',
        language: 'en',
        format: 'json',
      })

      const response = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?${params}`
      )

      if (!response.ok) {
        throw new Error(`Geocoding API error: ${response.status}`)
      }

      const data = await response.json()

      if (!data.results || data.results.length === 0) {
        error.value = `City not found: ${cityName}`
        return null
      }

      const result = data.results[0]
      return {
        name: result.name,
        country: result.country,
        latitude: result.latitude,
        longitude: result.longitude,
        admin1: result.admin1,
      }
    } catch (err: any) {
      error.value = err?.message || 'Geocoding failed.'
      return null
    } finally {
      loading.value = false
    }
  }

  async function reverseGeocode(lat: number, lon: number): Promise<string | null> {
    // Open-Meteo doesn't have a reverse geocoding endpoint, so we use a free alternative
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
        {
          headers: {
            'Accept-Language': 'en',
            'User-Agent': 'WeatherDashboard/1.0',
          },
        }
      )

      if (!response.ok) return null

      const data = await response.json()
      const address = data.address

      if (!address) return null

      // Return city/town/village name
      const cityName =
        address.city ||
        address.town ||
        address.village ||
        address.municipality ||
        address.county ||
        null

      return cityName
    } catch {
      return null
    }
  }

  return {
    loading,
    error,
    geocodeCity,
    reverseGeocode,
  }
}