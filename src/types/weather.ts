/**
 * Represents current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City or location name */
  city: string
  /** Country code (e.g. "US", "GB") */
  country: string
  /** Current temperature in Celsius */
  temperature: number
  /** "Feels like" temperature in Celsius */
  feelsLike: number
  /** Human-readable weather condition (e.g. "Partly Cloudy") */
  condition: string
  /** Weather condition code for icon mapping */
  conditionCode: WeatherConditionCode
  /** Relative humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction (e.g. "NW", "SE") */
  windDirection: string
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Visibility in kilometres */
  visibility: number
  /** UV index (0–11+) */
  uvIndex: number
  /** Sunrise time as locale string (e.g. "6:23 AM") */
  sunrise: string
  /** Sunset time as locale string (e.g. "8:14 PM") */
  sunset: string
  /** Last updated ISO timestamp */
  lastUpdated: string
}

/**
 * Represents weather data for a single forecast day.
 */
export interface ForecastDay {
  /** ISO date string (e.g. "2026-06-20") */
  date: string
  /** Short day label (e.g. "Mon", "Tue") */
  day: string
  /** High temperature in Celsius */
  high: number
  /** Low temperature in Celsius */
  low: number
  /** Human-readable condition */
  condition: string
  /** Weather condition code for icon mapping */
  conditionCode: WeatherConditionCode
  /** Chance of precipitation (0–100) */
  precipitationChance: number
}

/**
 * Top-level weather data payload.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
}

/**
 * Supported weather condition codes for icon/color mapping.
 */
export type WeatherConditionCode =
  | 'sunny'
  | 'partly-cloudy'
  | 'cloudy'
  | 'overcast'
  | 'rainy'
  | 'heavy-rain'
  | 'thunderstorm'
  | 'snowy'
  | 'foggy'
  | 'windy'
  | 'clear-night'
  | 'partly-cloudy-night'

/**
 * Maps a WeatherConditionCode to a display emoji icon.
 */
export const CONDITION_ICONS: Record<WeatherConditionCode, string> = {
  'sunny': '☀️',
  'partly-cloudy': '⛅',
  'cloudy': '🌥️',
  'overcast': '☁️',
  'rainy': '🌧️',
  'heavy-rain': '⛈️',
  'thunderstorm': '🌩️',
  'snowy': '❄️',
  'foggy': '🌫️',
  'windy': '💨',
  'clear-night': '🌙',
  'partly-cloudy-night': '🌤️',
}

/**
 * Maps a WeatherConditionCode to a Tailwind gradient class.
 */
export const CONDITION_GRADIENTS: Record<WeatherConditionCode, string> = {
  'sunny': 'from-amber-400 via-orange-400 to-yellow-500',
  'partly-cloudy': 'from-sky-400 via-sky-500 to-blue-600',
  'cloudy': 'from-slate-400 via-slate-500 to-slate-600',
  'overcast': 'from-gray-500 via-gray-600 to-gray-700',
  'rainy': 'from-blue-500 via-blue-600 to-indigo-700',
  'heavy-rain': 'from-blue-700 via-indigo-700 to-slate-800',
  'thunderstorm': 'from-gray-700 via-slate-800 to-gray-900',
  'snowy': 'from-sky-200 via-blue-200 to-slate-300',
  'foggy': 'from-gray-400 via-slate-400 to-gray-500',
  'windy': 'from-teal-400 via-cyan-500 to-sky-600',
  'clear-night': 'from-indigo-900 via-blue-950 to-slate-900',
  'partly-cloudy-night': 'from-indigo-800 via-slate-800 to-blue-900',
}