export interface CurrentWeatherData {
  temperature: number;
  apparentTemperature: number;
  weatherCode: number;
  windSpeed: number;
  windDirection: number;
  humidity: number;
  precipitation: number;
  isDay: number;
}

export interface DailyForecastData {
  date: string;
  weatherCode: number;
  tempMax: number;
  tempMin: number;
  precipitationSum: number;
  precipitationProbabilityMax: number;
  windSpeedMax: number;
}

export interface WeatherApiResponse {
  current: CurrentWeatherData;
  daily: DailyForecastData[];
}

const WEATHER_BASE_URL = 'https://api.open-meteo.com/v1';

export async function fetchWeatherByCoords(
  lat: number,
  lon: number
): Promise<WeatherApiResponse> {
  const params = new URLSearchParams({
    latitude: lat.toString(),
    longitude: lon.toString(),
    current: [
      'temperature_2m',
      'apparent_temperature',
      'weather_code',
      'wind_speed_10m',
      'wind_direction_10m',
      'relative_humidity_2m',
      'precipitation',
      'is_day',
    ].join(','),
    daily: [
      'weather_code',
      'temperature_2m_max',
      'temperature_2m_min',
      'precipitation_sum',
      'precipitation_probability_max',
      'wind_speed_10m_max',
    ].join(','),
    timezone: 'auto',
    forecast_days: '7',
  });

  const response = await fetch(`${WEATHER_BASE_URL}/forecast?${params}`);

  if (!response.ok) {
    throw new Error(`Weather API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  const current: CurrentWeatherData = {
    temperature: Math.round(data.current.temperature_2m),
    apparentTemperature: Math.round(data.current.apparent_temperature),
    weatherCode: data.current.weather_code,
    windSpeed: Math.round(data.current.wind_speed_10m),
    windDirection: data.current.wind_direction_10m,
    humidity: data.current.relative_humidity_2m,
    precipitation: data.current.precipitation,
    isDay: data.current.is_day,
  };

  const daily: DailyForecastData[] = data.daily.time.map(
    (date: string, i: number) => ({
      date,
      weatherCode: data.daily.weather_code[i],
      tempMax: Math.round(data.daily.temperature_2m_max[i]),
      tempMin: Math.round(data.daily.temperature_2m_min[i]),
      precipitationSum: data.daily.precipitation_sum[i] ?? 0,
      precipitationProbabilityMax: data.daily.precipitation_probability_max[i] ?? 0,
      windSpeedMax: Math.round(data.daily.wind_speed_10m_max[i]),
    })
  );

  return { current, daily };
}