import type { WeatherData } from '@/types/weather'

/**
 * Hardcoded mock weather payload.
 * Matches the WeatherData interface exactly.
 * Replace with real API response in Phase 2.
 */
export const mockWeatherData: WeatherData = {
  current: {
    city: 'San Francisco',
    country: 'US',
    temperature: 18,
    feelsLike: 16,
    condition: 'Partly Cloudy',
    conditionCode: 'partly-cloudy',
    humidity: 72,
    windSpeed: 24,
    windDirection: 'W',
    pressure: 1013,
    visibility: 16,
    uvIndex: 4,
    sunrise: '5:51 AM',
    sunset: '8:32 PM',
    lastUpdated: '2026-06-19T14:30:00Z',
  },
  forecast: [
    {
      date: '2026-06-19',
      day: 'Today',
      high: 20,
      low: 13,
      condition: 'Partly Cloudy',
      conditionCode: 'partly-cloudy',
      precipitationChance: 10,
    },
    {
      date: '2026-06-20',
      day: 'Sat',
      high: 22,
      low: 14,
      condition: 'Sunny',
      conditionCode: 'sunny',
      precipitationChance: 0,
    },
    {
      date: '2026-06-21',
      day: 'Sun',
      high: 24,
      low: 15,
      condition: 'Sunny',
      conditionCode: 'sunny',
      precipitationChance: 5,
    },
    {
      date: '2026-06-22',
      day: 'Mon',
      high: 19,
      low: 13,
      condition: 'Cloudy',
      conditionCode: 'cloudy',
      precipitationChance: 25,
    },
    {
      date: '2026-06-23',
      day: 'Tue',
      high: 15,
      low: 11,
      condition: 'Rainy',
      conditionCode: 'rainy',
      precipitationChance: 80,
    },
    {
      date: '2026-06-24',
      day: 'Wed',
      high: 14,
      low: 10,
      condition: 'Heavy Rain',
      conditionCode: 'heavy-rain',
      precipitationChance: 90,
    },
    {
      date: '2026-06-25',
      day: 'Thu',
      high: 17,
      low: 12,
      condition: 'Partly Cloudy',
      conditionCode: 'partly-cloudy',
      precipitationChance: 20,
    },
  ],
}