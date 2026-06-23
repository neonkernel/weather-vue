export interface GeocodingResult {
  lat: number
  lon: number
  displayName: string
  country: string
  countryCode: string
}

export interface WeatherCurrent {
  temperature: number
  feelsLike: number
  humidity: number
  windSpeed: number
  windDirection: number
  weatherCode: number
  weatherLabel: string
  weatherEmoji: string
  isDay: boolean
  uvIndex: number
  visibility: number
  precipitation: number
}

export interface ForecastDay {
  date: string
  dateFormatted: string
  tempMax: number
  tempMin: number
  weatherCode: number
  weatherLabel: string
  weatherEmoji: string
  precipitationSum: number
  windSpeedMax: number
  uvIndexMax: number
}

export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
  city: string
  country: string
  lastUpdated: string
}