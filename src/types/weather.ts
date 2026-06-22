/**
 * Represents current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City name */
  city: string
  /** Country code (ISO 3166-1 alpha-2) */
  country: string
  /** Temperature in Celsius */
  temperature: number
  /** "Feels like" temperature in Celsius */
  feelsLike: number
  /** Weather condition description (e.g. "Partly Cloudy") */
  condition: string
  /** Emoji or icon code representing the condition */
  icon: string
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
  /** Wind direction (e.g. "NW") */
  windDirection: string
  /** Visibility in kilometers */
  visibility: number
  /** UV Index (0–11+) */
  uvIndex: number
  /** Atmospheric pressure in hPa */
  pressure: number
  /** Sunrise time as locale string */
  sunrise: string
  /** Sunset time as locale string */
  sunset: string
  /** Last updated timestamp */
  lastUpdated: string
}

/**
 * Represents a single day in the forecast.
 */
export interface ForecastDay {
  /** ISO date string (YYYY-MM-DD) */
  date: string
  /** Short day name (e.g. "Mon") */
  day: string
  /** Weather condition description */
  condition: string
  /** Emoji or icon code */
  icon: string
  /** High temperature in Celsius */
  high: number
  /** Low temperature in Celsius */
  low: number
  /** Precipitation probability (0–100) */
  precipProbability: number
  /** Expected precipitation amount in mm */
  precipAmount: number
  /** Humidity percentage */
  humidity: number
  /** Wind speed in km/h */
  windSpeed: number
}

/**
 * Root weather data object combining current and forecast.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
  /** Timezone name (e.g. "America/New_York") */
  timezone: string
  /** Latitude of the location */
  lat: number
  /** Longitude of the location */
  lon: number
}