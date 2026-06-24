import type { WeatherData, ForecastData } from '../types/weather'

const BASE_URL = 'https://api.open-meteo.com/v1'
const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1'

export interface WeatherServiceResult {
  current: WeatherData
  forecast: ForecastData[]
}

async function fetchWeatherByCoords(lat: number, lon: number): Promise<WeatherServiceResult> {
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
      'precipitation',
      'surface_pressure',
      'visibility',
      'uv_index',
    ].join(','),
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

  const response = await fetch(`${BASE_URL}/forecast?${params}`)
  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return parseWeatherResponse(data)
}

async function fetchWeatherByCity(city: string): Promise<WeatherServiceResult> {
  // First geocode the city
  const geoParams = new URLSearchParams({
    name: city,
    count: '1',
    language: 'en',
    format: 'json',
  })

  const geoResponse = await fetch(`${GEOCODING_URL}/search?${geoParams}`)
  if (!geoResponse.ok) {
    throw new Error(`Geocoding API error: ${geoResponse.status}`)
  }

  const geoData = await geoResponse.json()
  if (!geoData.results || geoData.results.length === 0) {
    throw new Error(`City not found: ${city}`)
  }

  const { latitude, longitude } = geoData.results[0]
  return fetchWeatherByCoords(latitude, longitude)
}

function parseWeatherResponse(data: any): WeatherServiceResult {
  const current: WeatherData = {
    temperature: data.current.temperature_2m,
    feelsLike: data.current.apparent_temperature,
    humidity: data.current.relative_humidity_2m,
    weatherCode: data.current.weather_code,
    windSpeed: data.current.wind_speed_10m,
    windDirection: data.current.wind_direction_10m,
    precipitation: data.current.precipitation,
    pressure: data.current.surface_pressure,
    visibility: data.current.visibility,
    uvIndex: data.current.uv_index,
    time: data.current.time,
  }

  const forecast: ForecastData[] = data.daily.time.map((time: string, index: number) => ({
    time,
    weatherCode: data.daily.weather_code[index],
    tempMax: data.daily.temperature_2m_max[index],
    tempMin: data.daily.temperature_2m_min[index],
    precipitationSum: data.daily.precipitation_sum[index],
    windSpeedMax: data.daily.wind_speed_10m_max[index],
  }))

  return { current, forecast }
}

export const weatherService = {
  fetchByCoords: fetchWeatherByCoords,
  fetchByCity: fetchWeatherByCity,
}