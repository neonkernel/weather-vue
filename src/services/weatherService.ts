import type { WeatherData } from '../types/weather'
import { getWeatherDescription } from '../utils/weatherCodeMap'

const BASE_URL = 'https://api.open-meteo.com/v1/forecast'
const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'

async function geocodeCity(city: string): Promise<{ lat: number; lon: number; name: string }> {
  const response = await fetch(
    `${GEOCODING_URL}?name=${encodeURIComponent(city)}&count=1&language=en&format=json`
  )
  if (!response.ok) {
    throw new Error(`Geocoding failed: ${response.statusText}`)
  }
  const data = await response.json()
  if (!data.results || data.results.length === 0) {
    throw new Error(`City not found: ${city}`)
  }
  const result = data.results[0]
  return { lat: result.latitude, lon: result.longitude, name: result.name }
}

async function fetchWeatherData(lat: number, lon: number): Promise<any> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: [
      'temperature_2m',
      'relative_humidity_2m',
      'apparent_temperature',
      'weather_code',
      'wind_speed_10m',
      'wind_direction_10m',
      'surface_pressure',
      'visibility',
      'uv_index',
    ].join(','),
    hourly: 'temperature_2m,precipitation_probability,weather_code',
    daily: [
      'weather_code',
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_sum',
      'wind_speed_10m_max',
    ].join(','),
    timezone: 'auto',
    forecast_days: '7',
  })

  const response = await fetch(`${BASE_URL}?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Weather API error: ${response.statusText}`)
  }
  return response.json()
}

function mapApiResponseToWeatherData(data: any, cityName: string): WeatherData {
  const current = data.current
  const daily = data.daily

  const forecast = daily.time.map((date: string, i: number) => ({
    date,
    weatherCode: daily.weather_code[i],
    description: getWeatherDescription(daily.weather_code[i]),
    tempMax: daily.temperature_2m_max[i],
    tempMin: daily.temperature_2m_min[i],
    precipitationSum: daily.precipitation_sum[i],
    windSpeedMax: daily.wind_speed_10m_max[i],
  }))

  return {
    city: cityName,
    current: {
      temperature: current.temperature_2m,
      feelsLike: current.apparent_temperature,
      humidity: current.relative_humidity_2m,
      weatherCode: current.weather_code,
      description: getWeatherDescription(current.weather_code),
      windSpeed: current.wind_speed_10m,
      windDirection: current.wind_direction_10m,
      pressure: current.surface_pressure,
      visibility: current.visibility,
      uvIndex: current.uv_index,
    },
    forecast,
    timezone: data.timezone,
    lastUpdated: new Date().toISOString(),
  }
}

export async function fetchWeatherByCity(city: string): Promise<WeatherData> {
  const { lat, lon, name } = await geocodeCity(city)
  const data = await fetchWeatherData(lat, lon)
  return mapApiResponseToWeatherData(data, name)
}

export async function fetchWeatherByCoords(lat: number, lon: number, cityName?: string): Promise<WeatherData> {
  const data = await fetchWeatherData(lat, lon)

  let resolvedCityName = cityName || 'Current Location'

  if (!cityName) {
    try {
      const reverseResponse = await fetch(
        `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
      )
      if (reverseResponse.ok) {
        const reverseData = await reverseResponse.json()
        resolvedCityName =
          reverseData.address?.city ||
          reverseData.address?.town ||
          reverseData.address?.village ||
          reverseData.address?.county ||
          'Current Location'
      }
    } catch {
      resolvedCityName = 'Current Location'
    }
  }

  return mapApiResponseToWeatherData(data, resolvedCityName)
}