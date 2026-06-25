import type { WeatherData, ForecastData } from '../types/weather'

const BASE_URL = 'https://api.open-meteo.com/v1'
const GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1'

export interface WeatherApiResponse {
  current: WeatherData
  forecast: ForecastData[]
  cityName?: string
}

async function fetchWeatherByCoords(lat: number, lon: number): Promise<WeatherApiResponse> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: [
      'temperature_2m',
      'apparent_temperature',
      'relative_humidity_2m',
      'wind_speed_10m',
      'wind_direction_10m',
      'weather_code',
      'precipitation',
      'pressure_msl',
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
  return parseApiResponse(data)
}

async function fetchWeatherByCity(city: string): Promise<WeatherApiResponse> {
  // First geocode the city
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

  const location = geoData.results[0]
  const weatherData = await fetchWeatherByCoords(location.latitude, location.longitude)

  return {
    ...weatherData,
    cityName: `${location.name}${location.admin1 ? ', ' + location.admin1 : ''}, ${location.country}`,
  }
}

function parseApiResponse(data: any): WeatherApiResponse {
  const current: WeatherData = {
    temperature: data.current?.temperature_2m ?? 0,
    apparentTemperature: data.current?.apparent_temperature ?? 0,
    humidity: data.current?.relative_humidity_2m ?? 0,
    windSpeed: data.current?.wind_speed_10m ?? 0,
    windDirection: data.current?.wind_direction_10m ?? 0,
    weatherCode: data.current?.weather_code ?? 0,
    precipitation: data.current?.precipitation ?? 0,
    pressure: data.current?.pressure_msl ?? 0,
    visibility: data.current?.visibility ?? 0,
    uvIndex: data.current?.uv_index ?? 0,
    time: data.current?.time ?? '',
    unit: data.current_units?.temperature_2m ?? '°C',
  }

  const forecast: ForecastData[] = []
  if (data.daily) {
    const days = data.daily
    const count = days.time?.length ?? 0
    for (let i = 0; i < count; i++) {
      forecast.push({
        date: days.time[i],
        weatherCode: days.weather_code?.[i] ?? 0,
        tempMax: days.temperature_2m_max?.[i] ?? 0,
        tempMin: days.temperature_2m_min?.[i] ?? 0,
        precipitation: days.precipitation_sum?.[i] ?? 0,
        windSpeedMax: days.wind_speed_10m_max?.[i] ?? 0,
      })
    }
  }

  return { current, forecast }
}

export const weatherService = {
  fetchByCoords: fetchWeatherByCoords,
  fetchByCity: fetchWeatherByCity,
}