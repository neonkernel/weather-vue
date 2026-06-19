/**
 * Represents the current weather conditions for a location.
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
  /** Emoji or icon code representing the condition */
  icon: string
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction as compass string (e.g. "NW") */
  windDirection: string
  /** Visibility in kilometers */
  visibility: number
  /** UV index (0–11+) */
  uvIndex: number
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Sunrise time as ISO string or HH:MM */
  sunrise: string
  /** Sunset time as ISO string or HH:MM */
  sunset: string
  /** Timestamp of last data update */
  lastUpdated: string
}

/**
 * Represents a single day's weather forecast.
 */
export interface ForecastDay {
  /** Day label (e.g. "Mon", "Tuesday", or ISO date string) */
  day: string
  /** Short date string for display (e.g. "Jun 20") */
  date: string
  /** High temperature in Celsius */
  high: number
  /** Low temperature in Celsius */
  low: number
  /** Human-readable condition */
  condition: string
  /** Emoji or icon code for the condition */
  icon: string
  /** Precipitation probability percentage (0–100) */
  precipitationChance: number
  /** Humidity percentage */
  humidity: number
}

/**
 * Root weather data structure combining current conditions and forecast.
 */
export interface WeatherData {
  /** Current weather information */
  current: WeatherCurrent
  /** Array of daily forecasts (typically 7 days) */
  forecast: ForecastDay[]
  /** Units system in use */
  units: 'metric' | 'imperial'
  /** API provider name (used for attribution) */
  provider: string
}