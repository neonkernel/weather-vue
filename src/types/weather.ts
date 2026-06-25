export interface WeatherData {
  temperature: number
  feelsLike: number
  humidity: number
  windSpeed: number
  windDirection: number
  pressure: number
  visibility: number | null
  weatherCode: number
  description: string
  icon: string
  unit: 'C' | 'F'
}

export interface ForecastDay {
  date: string
  weatherCode: number
  description: string
  icon: string
  tempMax: number
  tempMin: number
  precipitationProbability: number
}