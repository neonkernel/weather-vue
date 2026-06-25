import type { WeatherData } from '../types/weather'
import { getCoordinatesForCity } from './geocodingService'

const OPEN_METEO_BASE = 'https://api.open-meteo.com/v1'

async function fetchWeatherFromCoords(lat: number, lon: number, cityName: string): Promise<WeatherData> {
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
    hourly: 'temperature_2m,precipitation_probability,weather_code',
    daily: [
      'weather_code',
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_sum',
      'wind_speed_10m_max',
      'sunrise',
      'sunset',
    ].join(','),
    timezone: 'auto',
    forecast_days: '7',
  })

  const response = await fetch(`${OPEN_METEO_BASE}/forecast?${params}`)

  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()

  return mapApiResponseToWeatherData(data, cityName, lat, lon)
}

export async function fetchWeatherByCity(city: string): Promise<WeatherData> {
  const coords = await getCoordinatesForCity(city)
  return fetchWeatherFromCoords(coords.lat, coords.lon, coords.name || city)
}

export async function fetchWeatherByCoords(lat: number, lon: number, cityName?: string): Promise<WeatherData> {
  // Reverse geocode to get city name if not provided
  let resolvedCityName = cityName || ''
  if (!resolvedCityName) {
    try {
      const reverseParams = new URLSearchParams({
        latitude: lat.toString(),
        longitude: lon.toString(),
        count: '1',
      })
      const geoResponse = await fetch(
        `https://geocoding-api.open-meteo.com/v1/reverse?${reverseParams}`
      )
      if (geoResponse.ok) {
        const geoData = await geoResponse.json()
        if (geoData.results && geoData.results.length > 0) {
          const r = geoData.results[0]
          resolvedCityName = r.name || `${lat.toFixed(2)}, ${lon.toFixed(2)}`
        }
      }
    } catch {
      resolvedCityName = `${lat.toFixed(2)}, ${lon.toFixed(2)}`
    }
  }

  return fetchWeatherFromCoords(lat, lon, resolvedCityName)
}

function mapApiResponseToWeatherData(data: any, cityName: string, lat: number, lon: number): WeatherData {
  const current = data.current || {}
  const daily = data.daily || {}
  const hourly = data.hourly || {}

  const dailyForecasts = (daily.time || []).map((time: string, i: number) => ({
    date: time,
    weatherCode: daily.weather_code?.[i] ?? 0,
    tempMax: daily.temperature_2m_max?.[i] ?? 0,
    tempMin: daily.temperature_2m_min?.[i] ?? 0,
    precipitationSum: daily.precipitation_sum?.[i] ?? 0,
    windSpeedMax: daily.wind_speed_10m_max?.[i] ?? 0,
    sunrise: daily.sunrise?.[i] ?? '',
    sunset: daily.sunset?.[i] ?? '',
  }))

  const hourlyForecasts = (hourly.time || []).slice(0, 24).map((time: string, i: number) => ({
    time,
    temperature: hourly.temperature_2m?.[i] ?? 0,
    precipitationProbability: hourly.precipitation_probability?.[i] ?? 0,
    weatherCode: hourly.weather_code?.[i] ?? 0,
  }))

  return {
    city: cityName,
    lat,
    lon,
    timezone: data.timezone || 'UTC',
    current: {
      temperature: current.temperature_2m ?? 0,
      apparentTemperature: current.apparent_temperature ?? 0,
      humidity: current.relative_humidity_2m ?? 0,
      weatherCode: current.weather_code ?? 0,
      windSpeed: current.wind_speed_10m ?? 0,
      windDirection: current.wind_direction_10m ?? 0,
      pressure: current.surface_pressure ?? 0,
      visibility: current.visibility ?? 0,
    },
    daily: dailyForecasts,
    hourly: hourlyForecasts,
  }
}