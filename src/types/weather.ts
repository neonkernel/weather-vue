/**
 * Represents current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City name */
  city: string
  /** Country code (e.g. "US") */
  country: string
  /** Current temperature in Celsius */
  temperature: number
  /** "Feels like" temperature in Celsius */
  feelsLike: number
  /** Human-readable weather condition (e.g. "Partly Cloudy") */
  condition: string
  /** Emoji or icon code representing the condition */
  icon: string
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction (e.g. "NW") */
  windDirection: string
  /** Visibility in kilometres */
  visibility: number
  /** UV index */
  uvIndex: number
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Sunrise time as "HH:MM" string */
  sunrise: string
  /** Sunset time as "HH:MM" string */
  sunset: string
  /** Timestamp of last update (ISO 8601) */
  lastUpdated: string
}

/**
 * Represents a single day in the forecast.
 */
export interface ForecastDay {
  /** Date string (e.g. "2026-06-19") */
  date: string
  /** Short day name (e.g. "Mon") */
  day: string
  /** High temperature in Celsius */
  high: number
  /** Low temperature in Celsius */
  low: number
  /** Human-readable condition */
  condition: string
  /** Emoji or icon code */
  icon: string
  /** Chance of precipitation (0–100) */
  precipitationChance: number
  /** Humidity percentage */
  humidity: number
}

/**
 * Top-level weather payload containing current conditions + forecast.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
}