import type { WeatherData, ForecastDay } from '../types/weather'
import { weatherCodeToDescription, weatherCodeToIcon } from '../utils/weatherCodeMap'

const BASE_URL = 'https://api.open-meteo.com/v1'

export interface WeatherFetchResult {
  current: WeatherData
  forecast: ForecastDay[]
}

async function fetchWeatherByCoords(lat: number, lon: number): Promise<WeatherFetchResult> {
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
    ].join(','),
    daily: [
      'weather_code',
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_probability_max',
    ].join(','),
    timezone: 'auto',
    forecast_days: '7',
  })

  const response = await fetch(`${BASE_URL}/forecast?${params}`)

  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return parseWeatherResponse(data)
}

async function fetchWeatherByCity(cityName: string): Promise<WeatherFetchResult> {
  // First geocode the city name
  const geoParams = new URLSearchParams({
    name: cityName,
    count: '1',
    language: 'en',
    format: 'json',
  })

  const geoResponse = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${geoParams}`)

  if (!geoResponse.ok) {
    throw new Error(`Geocoding API error: ${geoResponse.status}`)
  }

  const geoData = await geoResponse.json()

  if (!geoData.results || geoData.results.length === 0) {
    throw new Error(`City not found: ${cityName}`)
  }

  const { latitude, longitude } = geoData.results[0]
  return fetchWeatherByCoords(latitude, longitude)
}

function parseWeatherResponse(data: any): WeatherFetchResult {
  const current = data.current
  const daily = data.daily

  const weatherCode = current.weather_code ?? 0
  const description = weatherCodeToDescription(weatherCode)
  const icon = weatherCodeToIcon(weatherCode)

  const currentWeather: WeatherData = {
    temperature: Math.round(current.temperature_2m),
    feelsLike: Math.round(current.apparent_temperature),
    humidity: current.relative_humidity_2m,
    windSpeed: Math.round(current.wind_speed_10m),
    windDirection: current.wind_direction_10m,
    pressure: Math.round(current.surface_pressure),
    visibility: current.visibility != null ? Math.round(current.visibility / 1000) : null,
    weatherCode,
    description,
    icon,
    unit: 'C',
  }

  const forecast: ForecastDay[] = (daily.time as string[]).map((date: string, i: number) => ({
    date,
    weatherCode: daily.weather_code[i],
    description: weatherCodeToDescription(daily.weather_code[i]),
    icon: weatherCodeToIcon(daily.weather_code[i]),
    tempMax: Math.round(daily.temperature_2m_max[i]),
    tempMin: Math.round(daily.temperature_2m_min[i]),
    precipitationProbability: daily.precipitation_probability_max[i],
  }))

  return { current: currentWeather, forecast }
}

export const weatherService = {
  fetchWeatherByCoords,
  fetchWeatherByCity,
}