export interface GeocodingResult {
  lat: number
  lon: number
  name: string
  country: string
  admin1?: string
}

export async function getCoordinatesForCity(city: string): Promise<GeocodingResult> {
  const params = new URLSearchParams({
    name: city,
    count: '1',
    language: 'en',
    format: 'json',
  })

  const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`)

  if (!response.ok) {
    throw new Error(`Geocoding API error: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()

  if (!data.results || data.results.length === 0) {
    throw new Error(`City not found: ${city}`)
  }

  const result = data.results[0]
  return {
    lat: result.latitude,
    lon: result.longitude,
    name: result.name,
    country: result.country,
    admin1: result.admin1,
  }
}