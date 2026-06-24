const BASE_URL = 'https://api.open-meteo.com/v1'
const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1'

export interface WeatherData {
  current: {
    temperature_2m: number
    relative_humidity_2m: number
    apparent_temperature: number
    weather_code: number
    wind_speed_10m: number
    wind_direction_10m: number
    precipitation: number
    surface_pressure: number
    visibility?: number
    uv_index?: number
  }
  hourly?: {
    time: string[]
    temperature_2m: number[]
    weather_code: number[]
    precipitation_probability: number[]
  }
  daily?: {
    time: string[]
    temperature_2m_max: number[]
    temperature_2m_min: number[]
    weather_code: number[]
    precipitation_sum: number[]
    wind_speed_10m_max: number[]
    precipitation_probability_max: number[]
  }
  latitude: number
  longitude: number
  timezone: string
}

export interface GeocodingResult {
  id: number
  name: string
  latitude: number
  longitude: number
  country: string
  admin1?: string
}

const WEATHER_PARAMS = [
  'temperature_2m',
  'relative_humidity_2m',
  'apparent_temperature',
  'weather_code',
  'wind_speed_10m',
  'wind_direction_10m',
  'precipitation',
  'surface_pressure',
].join(',')

const HOURLY_PARAMS = [
  'temperature_2m',
  'weather_code',
  'precipitation_probability',
].join(',')

const DAILY_PARAMS = [
  'temperature_2m_max',
  'temperature_2m_min',
  'weather_code',
  'precipitation_sum',
  'wind_speed_10m_max',
  'precipitation_probability_max',
].join(',')

export async function fetchWeatherByCoords(
  lat: number,
  lon: number
): Promise<WeatherData> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: WEATHER_PARAMS,
    hourly: HOURLY_PARAMS,
    daily: DAILY_PARAMS,
    forecast_days: '7',
    timezone: 'auto',
  })

  const response = await fetch(`${BASE_URL}/forecast?${params}`)
  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

export async function fetchWeatherByCity(city: string): Promise<{
  weather: WeatherData
  location: GeocodingResult
}> {
  // First geocode the city name
  const geoParams = new URLSearchParams({
    name: city,
    count: '1',
    language: 'en',
    format: 'json',
  })

  const geoResponse = await fetch(`${GEOCODING_URL}/search?${geoParams}`)
  if (!geoResponse.ok) {
    throw new Error(`Geocoding API error: ${geoResponse.status} ${geoResponse.statusText}`)
  }

  const geoData = await geoResponse.json()
  if (!geoData.results || geoData.results.length === 0) {
    throw new Error(`City not found: ${city}`)
  }

  const location: GeocodingResult = geoData.results[0]
  const weather = await fetchWeatherByCoords(location.latitude, location.longitude)

  return { weather, location }
}

export async function reverseGeocode(lat: number, lon: number): Promise<string> {
  // Open-Meteo doesn't have reverse geocoding, so we use a simple approach
  // with the nominatim API or return a coordinate string as fallback
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
    if (!response.ok) throw new Error('Reverse geocoding failed')
    const data = await response.json()
    const city =
      data.address?.city ||
      data.address?.town ||
      data.address?.village ||
      data.address?.county ||
      data.address?.state ||
      'Unknown Location'
    return city
  } catch {
    return `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`
  }
}