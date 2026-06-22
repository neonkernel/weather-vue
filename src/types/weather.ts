/**
 * Represents the current weather conditions for a location.
 */
export interface WeatherCurrent {
  /** City or location name */
  city: string
  /** ISO 3166-1 alpha-2 country code (e.g. "US") */
  country: string
  /** Current temperature in Celsius */
  tempC: number
  /** "Feels like" temperature in Celsius */
  feelsLikeC: number
  /** Human-readable weather condition (e.g. "Partly Cloudy") */
  condition: string
  /** Emoji or icon code representing the condition */
  conditionIcon: string
  /** Humidity percentage (0–100) */
  humidity: number
  /** Wind speed in km/h */
  windKph: number
  /** Wind direction abbreviation (e.g. "NW") */
  windDir: string
  /** Atmospheric pressure in hPa */
  pressureHpa: number
  /** Visibility in kilometres */
  visibilityKm: number
  /** UV index (0–11+) */
  uvIndex: number
  /** Dew point in Celsius */
  dewPointC: number
  /** ISO 8601 datetime string of last observation */
  lastUpdated: string
  /** Sunrise time (local, HH:mm) */
  sunrise: string
  /** Sunset time (local, HH:mm) */
  sunset: string
}

/**
 * Represents a single day in the weather forecast.
 */
export interface ForecastDay {
  /** ISO 8601 date string (YYYY-MM-DD) */
  date: string
  /** Short weekday label (e.g. "Mon") */
  dayLabel: string
  /** Maximum temperature in Celsius */
  maxTempC: number
  /** Minimum temperature in Celsius */
  minTempC: number
  /** Human-readable weather condition */
  condition: string
  /** Emoji or icon code representing the condition */
  conditionIcon: string
  /** Probability of precipitation (0–100) */
  precipChance: number
  /** Total precipitation in mm */
  precipMm: number
  /** Average humidity percentage */
  humidity: number
  /** Maximum wind speed in km/h */
  maxWindKph: number
  /** UV index for the day */
  uvIndex: number
}

/**
 * Root weather data structure passed as props through the component tree.
 */
export interface WeatherData {
  current: WeatherCurrent
  forecast: ForecastDay[]
}