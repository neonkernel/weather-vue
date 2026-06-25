import type { WeatherData } from '../types/weather'

const BASE_URL = 'https://api.open-meteo.com/v1/forecast'

interface OpenMeteoResponse {
  latitude: number
  longitude: number
  current_weather: {
    temperature: number
    windspeed: number
    weathercode: number
    time: string
  }
  hourly: {
    time: string[]
    temperature_2m: number[]
    relativehumidity_2m: number[]
    precipitation_probability: number[]
    weathercode: number[]
  }
  daily: {
    time: string[]
    temperature_2m_max: number[]
    temperature_2m_min: number[]
    weathercode: number[]
    precipitation_probability_max: number[]
  }
}

async function fetchFromOpenMeteo(lat: number, lon: number): Promise<OpenMeteoResponse> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current_weather: 'true',
    hourly: 'temperature_2m,relativehumidity_2m,precipitation_probability,weathercode',
    daily: 'temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max',
    timezone: 'auto',
    forecast_days: '7',
  })

  const response = await fetch(`${BASE_URL}?${params}`)
  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

function mapToWeatherData(data: OpenMeteoResponse, cityName?: string): WeatherData {
  return {
    city: cityName || `${data.latitude.toFixed(2)}, ${data.longitude.toFixed(2)}`,
    lat: data.latitude,
    lon: data.longitude,
    current: {
      temperature: data.current_weather.temperature,
      windspeed: data.current_weather.windspeed,
      weathercode: data.current_weather.weathercode,
      time: data.current_weather.time,
    },
    hourly: {
      time: data.hourly.time,
      temperature: data.hourly.temperature_2m,
      humidity: data.hourly.relativehumidity_2m,
      precipitationProbability: data.hourly.precipitation_probability,
      weathercode: data.hourly.weathercode,
    },
    daily: {
      time: data.daily.time,
      tempMax: data.daily.temperature_2m_max,
      tempMin: data.daily.temperature_2m_min,
      weathercode: data.daily.weathercode,
      precipitationProbabilityMax: data.daily.precipitation_probability_max,
    },
  }
}

export async function fetchWeatherByCoords(
  lat: number,
  lon: number,
  cityName?: string
): Promise<WeatherData> {
  const data = await fetchFromOpenMeteo(lat, lon)
  return mapToWeatherData(data, cityName)
}

export async function fetchWeatherByCity(city: string): Promise<WeatherData> {
  // First geocode the city to get coordinates
  const geocodeUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=en&format=json`
  const geocodeResponse = await fetch(geocodeUrl)

  if (!geocodeResponse.ok) {
    throw new Error(`Geocoding API error: ${geocodeResponse.status}`)
  }

  const geocodeData = await geocodeResponse.json()

  if (!geocodeData.results || geocodeData.results.length === 0) {
    throw new Error(`City not found: ${city}`)
  }

  const { latitude, longitude, name, country } = geocodeData.results[0]
  const cityLabel = country ? `${name}, ${country}` : name

  const data = await fetchFromOpenMeteo(latitude, longitude)
  return mapToWeatherData(data, cityLabel)
}