export interface CurrentWeather {
  temperature: number
  apparentTemperature: number
  humidity: number
  weatherCode: number
  windSpeed: number
  windDirection: number
  pressure: number
  visibility: number
}

export interface DailyForecast {
  date: string
  weatherCode: number
  tempMax: number
  tempMin: number
  precipitationSum: number
  windSpeedMax: number
  sunrise: string
  sunset: string
}

export interface HourlyForecast {
  time: string
  temperature: number
  precipitationProbability: number
  weatherCode: number
}

export interface WeatherData {
  city: string
  lat: number
  lon: number
  timezone: string
  current: CurrentWeather
  daily: DailyForecast[]
  hourly: HourlyForecast[]
}