/**
 * Represents current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City or location name */
  city: string
  /** Country code, e.g. "US" */
  country: string
  /** Current temperature in Celsius */
  temperature: number
  /** Feels-like temperature in Celsius */
  feelsLike: number
  /** Short condition description, e.g. "Partly Cloudy" */
  condition: string
  /** Emoji or icon code representing the condition */
  icon: string
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction, e.g. "NW" */
  windDirection: string
  /** Visibility in kilometres */
  visibility: number
  /** UV index (0–11+) */
  uvIndex: number
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Sunrise time, e.g. "06:14 AM" */
  sunrise: string
  /** Sunset time, e.g. "08:32 PM" */
  sunset: string
  /** Last updated timestamp (ISO 8601) */
  updatedAt: string
}

/**
 * Represents a single day in the forecast.
 */
export interface ForecastDay {
  /** ISO date string, e.g. "2026-06-22" */
  date: string
  /** Short day label, e.g. "Mon" */
  dayLabel: string
  /** High temperature for the day in Celsius */
  high: number
  /** Low temperature for the day in Celsius */
  low: number
  /** Short condition description */
  condition: string
  /** Emoji or icon code */
  icon: string
  /** Precipitation chance (0–100) */
  precipChance: number
}

/**
 * Top-level shape of all weather data used by the app.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
}