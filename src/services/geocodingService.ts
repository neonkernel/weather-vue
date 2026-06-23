import type { GeocodingResult } from '../types/weather'

const GEOCODING_API_BASE = 'https://geocoding-api.open-meteo.com/v1/search'

export interface RawGeocodingResult {
  id: number
  name: string
  latitude: number
  longitude: number
  country: string
  country_code: string
  admin1?: string
  admin2?: string
}

export interface GeocodingApiResponse {
  results?: RawGeocodingResult[]
  generationtime_ms: number
}

/**
 * Search for a city using the Open-Meteo Geocoding API
 * @param cityName - The name of the city to search for
 * @param count - Number of results to return (default 1)
 */
export async function searchCity(cityName: string, count = 1): Promise<GeocodingResult[]> {
  if (!cityName.trim()) {
    throw new Error('City name cannot be empty')
  }

  const params = new URLSearchParams({
    name: cityName.trim(),
    count: String(count),
    language: 'en',
    format: 'json',
  })

  const url = `${GEOCODING_API_BASE}?${params.toString()}`

  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Geocoding API error: ${response.status} ${response.statusText}`)
  }

  const data: GeocodingApiResponse = await response.json()

  if (!data.results || data.results.length === 0) {
    throw new Error(`No results found for "${cityName}". Please check the city name and try again.`)
  }

  return data.results.map((r) => ({
    lat: r.latitude,
    lon: r.longitude,
    displayName: r.admin1 ? `${r.name}, ${r.admin1}` : r.name,
    country: r.country,
    countryCode: r.country_code,
  }))
}

/**
 * Get the first geocoding result for a city name
 */
export async function geocodeCity(cityName: string): Promise<GeocodingResult> {
  const results = await searchCity(cityName, 1)
  return results[0]
}