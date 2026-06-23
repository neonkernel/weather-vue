// Re-export service types for backward compatibility
export type { CurrentWeatherData, DailyForecastData, WeatherApiResponse } from '../services/weatherService';
export type { GeocodingResult } from '../services/geocodingService';

// Legacy mock types (kept for reference)
export interface WeatherCurrent {
  city: string;
  temperature: number;
  condition: string;
  humidity: number;
  windSpeed: number;
  feelsLike: number;
}

export interface ForecastDay {
  day: string;
  high: number;
  low: number;
  condition: string;
}