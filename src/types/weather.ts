/**
 * Represents current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City or location name */
  city: string
  /** Country code (e.g. "US", "GB") */
  country: string
  /** Temperature in Celsius */
  temperature: number
  /** "Feels like" temperature in Celsius */
  feelsLike: number
  /** Short description (e.g. "Partly Cloudy") */
  condition: string
  /** Weather condition code for icon mapping */
  conditionCode: WeatherConditionCode
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction (e.g. "NW") */
  windDirection: string
  /** Visibility in km */
  visibility: number
  /** UV Index */
  uvIndex: number
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Sunrise time as ISO string or HH:MM */
  sunrise: string
  /** Sunset time as ISO string or HH:MM */
  sunset: string
  /** Last updated timestamp */
  updatedAt: string
}

/**
 * Represents a single day's forecast.
 */
export interface ForecastDay {
  /** Date as ISO string (YYYY-MM-DD) */
  date: string
  /** Day of week label (e.g. "Mon", "Tuesday") */
  dayLabel: string
  /** High temperature in Celsius */
  tempHigh: number
  /** Low temperature in Celsius */
  tempLow: number
  /** Short description */
  condition: string
  /** Weather condition code for icon mapping */
  conditionCode: WeatherConditionCode
  /** Chance of precipitation (0–100) */
  precipChance: number
}

/**
 * Aggregated weather payload returned from the data layer.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
}

/**
 * Supported weather condition codes used for icon/color mapping.
 */
export type WeatherConditionCode =
  | 'clear-day'
  | 'clear-night'
  | 'partly-cloudy-day'
  | 'partly-cloudy-night'
  | 'cloudy'
  | 'rain'
  | 'drizzle'
  | 'thunderstorm'
  | 'snow'
  | 'sleet'
  | 'wind'
  | 'fog'
  | 'hail'

/**
 * Maps a WeatherConditionCode to a display emoji icon.
 */
export const CONDITION_ICONS: Record<WeatherConditionCode, string> = {
  'clear-day': '☀️',
  'clear-night': '🌙',
  'partly-cloudy-day': '⛅',
  'partly-cloudy-night': '🌙',
  cloudy: '☁️',
  rain: '🌧️',
  drizzle: '🌦️',
  thunderstorm: '⛈️',
  snow: '❄️',
  sleet: '🌨️',
  wind: '💨',
  fog: '🌫️',
  hail: '🌩️',
}

/**
 * Maps a WeatherConditionCode to a Tailwind background gradient class.
 */
export const CONDITION_GRADIENTS: Record<WeatherConditionCode, string> = {
  'clear-day': 'from-sky-400 via-blue-500 to-indigo-600',
  'clear-night': 'from-indigo-950 via-slate-900 to-slate-800',
  'partly-cloudy-day': 'from-sky-300 via-blue-400 to-slate-500',
  'partly-cloudy-night': 'from-slate-800 via-indigo-900 to-slate-900',
  cloudy: 'from-slate-400 via-slate-500 to-slate-600',
  rain: 'from-slate-600 via-blue-800 to-slate-700',
  drizzle: 'from-slate-500 via-blue-600 to-slate-600',
  thunderstorm: 'from-slate-800 via-slate-900 to-indigo-950',
  snow: 'from-slate-100 via-blue-100 to-slate-200',
  sleet: 'from-slate-300 via-blue-300 to-slate-400',
  wind: 'from-teal-400 via-cyan-500 to-blue-500',
  fog: 'from-slate-300 via-gray-400 to-slate-400',
  hail: 'from-slate-600 via-gray-700 to-slate-800',
}