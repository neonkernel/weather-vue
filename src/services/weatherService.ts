import type { WeatherCurrent, ForecastDay, WeatherData } from '../types/weather'
import type { GeocodingResult } from '../types/weather'
import { getWeatherInfo } from '../utils/weatherCodeMap'
import { formatDateRelative } from '../utils/unitConverters'

const WEATHER_API_BASE = 'https://api.open-meteo.com/v1/forecast'

export interface OpenMeteoCurrentWeather {
  time: string
  interval: number
  temperature_2m: number
  relative_humidity_2m: number
  apparent_temperature: number
  is_day: number
  precipitation: number
  weather_code: number
  wind_speed_10m: number
  wind_direction_10m: number
  uv_index: number
  visibility: number
}

export interface OpenMeteoDaily {
  time: string[]
  weather_code: number[]
  temperature_2m_max: number[]
  temperature_2m_min: number[]
  precipitation_sum: number[]
  wind_speed_10m_max: number[]
  uv_index_max: number[]
}

export interface OpenMeteoApiResponse {
  latitude: number
  longitude: number
  generationtime_ms: number
  utc_offset_seconds: number
  timezone: string
  timezone_abbreviation: string
  current: OpenMeteoCurrentWeather
  daily: OpenMeteoDaily
}

/**
 * Fetch weather data from Open-Meteo API
 */
export async function fetchWeatherData(
  lat: number,
  lon: number,
): Promise<OpenMeteoApiResponse> {
  const params = new URLSearchParams({
    latitude: String(lat),
    longitude: String(lon),
    current: [
      'temperature_2m',
      'relative_humidity_2m',
      'apparent_temperature',
      'is_day',
      'precipitation',
      'weather_code',
      'wind_speed_10m',
      'wind_direction_10m',
      'uv_index',
      'visibility',
    ].join(','),
    daily: [
      'weather_code',
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_sum',
      'wind_speed_10m_max',
      'uv_index_max',
    ].join(','),
    forecast_days: '7',
    wind_speed_unit: 'kmh',
    timezone: 'auto',
  })

  const url = `${WEATHER_API_BASE}?${params.toString()}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }

  const data: OpenMeteoApiResponse = await response.json()
  return data
}

/**
 * Transform raw Open-Meteo response into our WeatherData shape
 */
export function transformWeatherData(
  raw: OpenMeteoApiResponse,
  location: GeocodingResult,
): WeatherData {
  const { current, daily } = raw

  const currentWeatherInfo = getWeatherInfo(current.weather_code)

  const weatherCurrent: WeatherCurrent = {
    temperature: Math.round(current.temperature_2m),
    feelsLike: Math.round(current.apparent_temperature),
    humidity: current.relative_humidity_2m,
    windSpeed: Math.round(current.wind_speed_10m),
    windDirection: current.wind_direction_10m,
    weatherCode: current.weather_code,
    weatherLabel: currentWeatherInfo.label,
    weatherEmoji: currentWeatherInfo.emoji,
    isDay: current.is_day === 1,
    uvIndex: current.uv_index ?? 0,
    visibility: Math.round((current.visibility ?? 0) / 1000), // convert m to km
    precipitation: current.precipitation,
  }

  const forecast: ForecastDay[] = daily.time.map((date, index) => {
    const forecastWeatherInfo = getWeatherInfo(daily.weather_code[index])
    return {
      date,
      dateFormatted: formatDateRelative(date),
      tempMax: Math.round(daily.temperature_2m_max[index]),
      tempMin: Math.round(daily.temperature_2m_min[index]),
      weatherCode: daily.weather_code[index],
      weatherLabel: forecastWeatherInfo.label,
      weatherEmoji: forecastWeatherInfo.emoji,
      precipitationSum: daily.precipitation_sum[index],
      windSpeedMax: Math.round(daily.wind_speed_10m_max[index]),
      uvIndexMax: daily.uv_index_max[index] ?? 0,
    }
  })

  return {
    current: weatherCurrent,
    forecast,
    city: location.displayName,
    country: location.country,
    lastUpdated: new Date().toISOString(),
  }
}

/**
 * High-level function: fetch and transform weather for a given location
 */
export async function getWeatherForLocation(location: GeocodingResult): Promise<WeatherData> {
  const raw = await fetchWeatherData(location.lat, location.lon)
  return transformWeatherData(raw, location)
}