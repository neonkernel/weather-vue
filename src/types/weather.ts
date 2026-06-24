export interface WeatherData {
  temperature: number
  feelsLike: number
  humidity: number
  weatherCode: number
  windSpeed: number
  windDirection: number
  precipitation: number
  pressure: number
  visibility: number
  uvIndex: number
  time: string
}

export interface ForecastData {
  time: string
  weatherCode: number
  tempMax: number
  tempMin: number
  precipitationSum: number
  windSpeedMax: number
}