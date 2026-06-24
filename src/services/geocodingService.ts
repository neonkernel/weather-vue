const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'

export interface GeocodingResult {
  id: number
  name: string
  latitude: number
  longitude: number
  country: string
  admin1?: string
}

export interface GeocodingResponse {
  results?: GeocodingResult[]
}

export async function searchCity(query: string): Promise<GeocodingResult[]> {
  const url = new URL(GEOCODING_URL)
  url.searchParams.set('name', query)
  url.searchParams.set('count', '5')
  url.searchParams.set('language', 'en')
  url.searchParams.set('format', 'json')

  const response = await fetch(url.toString())

  if (!response.ok) {
    throw new Error(`Geocoding API error: ${response.status} ${response.statusText}`)
  }

  const data: GeocodingResponse = await response.json()
  return data.results ?? []
}

export async function reverseGeocode(lat: number, lon: number): Promise<string> {
  // Open-Meteo doesn't provide reverse geocoding, so we use a simple approach
  // In production you'd use a proper reverse geocoding API
  // For now, return coordinates as fallback
  try {
    const url = new URL('https://nominatim.openstreetmap.org/reverse')
    url.searchParams.set('lat', lat.toString())
    url.searchParams.set('lon', lon.toString())
    url.searchParams.set('format', 'json')

    const response = await fetch(url.toString(), {
      headers: {
        'Accept-Language': 'en',
        'User-Agent': 'WeatherDashboard/1.0',
      },
    })

    if (!response.ok) {
      return `${lat.toFixed(2)}, ${lon.toFixed(2)}`
    }

    const data = await response.json()
    const city =
      data.address?.city ||
      data.address?.town ||
      data.address?.village ||
      data.address?.county ||
      data.address?.state ||
      data.address?.country ||
      `${lat.toFixed(2)}, ${lon.toFixed(2)}`

    return city
  } catch {
    return `${lat.toFixed(2)}, ${lon.toFixed(2)}`
  }
}