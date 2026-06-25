export interface CurrentWeather {
  temperature: number
  windspeed: number
  weathercode: number
  time: string
}

export interface HourlyWeather {
  time: string[]
  temperature: number[]
  humidity: number[]
  precipitationProbability: number[]
  weathercode: number[]
}

export interface DailyWeather {
  time: string[]
  tempMax: number[]
  tempMin: number[]
  weathercode: number[]
  precipitationProbabilityMax: number[]
}

export interface WeatherData {
  city: string
  lat: number
  lon: number
  current: CurrentWeather
  hourly: HourlyWeather
  daily: DailyWeather
}