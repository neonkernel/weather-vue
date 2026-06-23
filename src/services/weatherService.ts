import type { WeatherCurrent, ForecastDay } from '../types/weather';

const WEATHER_BASE_URL = 'https://api.open-meteo.com/v1/forecast';

export interface OpenMeteoResponse {
  latitude: number;
  longitude: number;
  timezone: string;
  current: {
    time: string;
    temperature_2m: number;
    apparent_temperature: number;
    relative_humidity_2m: number;
    wind_speed_10m: number;
    wind_direction_10m: number;
    weather_code: number;
    is_day: number;
    precipitation: number;
  };
  daily: {
    time: string[];
    temperature_2m_max: number[];
    temperature_2m_min: number[];
    precipitation_sum: number[];
    wind_speed_10m_max: number[];
    weather_code: number[];
    uv_index_max: number[];
  };
}

/**
 * Fetch raw weather data from Open-Meteo for a given lat/lon.
 */
export async function fetchWeatherData(lat: number, lon: number): Promise<OpenMeteoResponse> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: [
      'temperature_2m',
      'apparent_temperature',
      'relative_humidity_2m',
      'wind_speed_10m',
      'wind_direction_10m',
      'weather_code',
      'is_day',
      'precipitation',
    ].join(','),
    daily: [
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_sum',
      'wind_speed_10m_max',
      'weather_code',
      'uv_index_max',
    ].join(','),
    wind_speed_unit: 'kmh',
    timezone: 'auto',
    forecast_days: '7',
  });

  const response = await fetch(`${WEATHER_BASE_URL}?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Transform raw Open-Meteo current weather into our WeatherCurrent type.
 */
export function transformCurrentWeather(raw: OpenMeteoResponse): WeatherCurrent {
  const c = raw.current;
  return {
    temperature: Math.round(c.temperature_2m),
    feelsLike: Math.round(c.apparent_temperature),
    humidity: c.relative_humidity_2m,
    windSpeed: Math.round(c.wind_speed_10m),
    windDirection: c.wind_direction_10m,
    weatherCode: c.weather_code,
    isDay: c.is_day,
    precipitation: c.precipitation,
    uvIndex: 0, // Not available in current endpoint; use daily[0]
  };
}

/**
 * Transform raw Open-Meteo daily forecast into our ForecastDay[] type.
 */
export function transformForecast(raw: OpenMeteoResponse): ForecastDay[] {
  const d = raw.daily;
  return d.time.map((date, i) => ({
    date,
    temperatureMax: Math.round(d.temperature_2m_max[i]),
    temperatureMin: Math.round(d.temperature_2m_min[i]),
    precipitationSum: d.precipitation_sum[i] ?? 0,
    windSpeedMax: Math.round(d.wind_speed_10m_max[i]),
    weatherCode: d.weather_code[i],
    uvIndexMax: d.uv_index_max[i] ?? 0,
  }));
}