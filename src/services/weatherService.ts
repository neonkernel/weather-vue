import type { GeoLocation, WeatherCurrent, ForecastDay, WeatherData } from '../types/weather';
import { getWeatherInfo } from '../utils/weatherCodeMap';
import { friendlyDate } from '../utils/unitConverters';

const WEATHER_BASE = 'https://api.open-meteo.com/v1/forecast';

interface OpenMeteoCurrentUnits {
  temperature_2m: string;
  apparent_temperature: string;
  relative_humidity_2m: string;
  wind_speed_10m: string;
  wind_direction_10m: string;
  weather_code: string;
  is_day: string;
  precipitation_probability: string;
  uv_index: string;
}

interface OpenMeteoCurrent {
  time: string;
  temperature_2m: number;
  apparent_temperature: number;
  relative_humidity_2m: number;
  wind_speed_10m: number;
  wind_direction_10m: number;
  weather_code: number;
  is_day: number;
  precipitation_probability: number;
  uv_index: number;
}

interface OpenMeteoDailyUnits {
  time: string;
  temperature_2m_max: string;
  temperature_2m_min: string;
  weather_code: string;
  precipitation_sum: string;
  precipitation_probability_max: string;
  wind_speed_10m_max: string;
  uv_index_max: string;
}

interface OpenMeteoDaily {
  time: string[];
  temperature_2m_max: number[];
  temperature_2m_min: number[];
  weather_code: number[];
  precipitation_sum: number[];
  precipitation_probability_max: number[];
  wind_speed_10m_max: number[];
  uv_index_max: number[];
}

export interface OpenMeteoResponse {
  latitude: number;
  longitude: number;
  timezone: string;
  current_units: OpenMeteoCurrentUnits;
  current: OpenMeteoCurrent;
  daily_units: OpenMeteoDailyUnits;
  daily: OpenMeteoDaily;
}

/**
 * Fetch raw weather data from Open-Meteo for a given lat/lon.
 */
export async function fetchWeatherRaw(lat: number, lon: number): Promise<OpenMeteoResponse> {
  const params = new URLSearchParams({
    latitude: String(lat),
    longitude: String(lon),
    current: [
      'temperature_2m',
      'apparent_temperature',
      'relative_humidity_2m',
      'wind_speed_10m',
      'wind_direction_10m',
      'weather_code',
      'is_day',
      'precipitation_probability',
      'uv_index',
    ].join(','),
    daily: [
      'temperature_2m_max',
      'temperature_2m_min',
      'weather_code',
      'precipitation_sum',
      'precipitation_probability_max',
      'wind_speed_10m_max',
      'uv_index_max',
    ].join(','),
    wind_speed_unit: 'kmh',
    forecast_days: '7',
    timezone: 'auto',
  });

  const response = await fetch(`${WEATHER_BASE}?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Weather request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<OpenMeteoResponse>;
}

/**
 * Transform raw Open-Meteo response into our typed WeatherData shape.
 */
export function transformWeatherData(raw: OpenMeteoResponse, location: GeoLocation): WeatherData {
  const c = raw.current;
  const d = raw.daily;

  const currentInfo = getWeatherInfo(c.weather_code);

  const current: WeatherCurrent = {
    temperature: Math.round(c.temperature_2m),
    feelsLike: Math.round(c.apparent_temperature),
    humidity: c.relative_humidity_2m,
    windSpeed: Math.round(c.wind_speed_10m),
    windDirection: c.wind_direction_10m,
    weatherCode: c.weather_code,
    weatherLabel: currentInfo.label,
    weatherEmoji: currentInfo.emoji,
    isDay: c.is_day === 1,
    precipitationProbability: c.precipitation_probability ?? 0,
    uvIndex: c.uv_index ?? 0,
  };

  const forecast: ForecastDay[] = d.time.map((dateStr, i) => {
    const info = getWeatherInfo(d.weather_code[i]);
    return {
      date: dateStr,
      dateFormatted: friendlyDate(dateStr),
      tempMax: Math.round(d.temperature_2m_max[i]),
      tempMin: Math.round(d.temperature_2m_min[i]),
      weatherCode: d.weather_code[i],
      weatherLabel: info.label,
      weatherEmoji: info.emoji,
      precipitationSum: Math.round((d.precipitation_sum[i] ?? 0) * 10) / 10,
      precipitationProbability: d.precipitation_probability_max[i] ?? 0,
      windSpeedMax: Math.round(d.wind_speed_10m_max[i]),
      uvIndexMax: Math.round(d.uv_index_max[i] ?? 0),
    };
  });

  return {
    location,
    current,
    forecast,
    fetchedAt: new Date().toISOString(),
  };
}

/**
 * High-level function: fetch + transform weather for a location.
 */
export async function fetchWeatherForLocation(location: GeoLocation): Promise<WeatherData> {
  const raw = await fetchWeatherRaw(location.lat, location.lon);
  return transformWeatherData(raw, location);
}