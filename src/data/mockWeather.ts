import type { WeatherData } from '@/types/weather'

/**
 * Hardcoded mock weather payload.
 * This mirrors the WeatherData interface and is used during Phase 1
 * before real API integration is added in Phase 2.
 */
export const mockWeatherData: WeatherData = {
  current: {
    city: 'San Francisco',
    country: 'US',
    temperature: 18,
    feelsLike: 16,
    condition: 'Partly Cloudy',
    conditionCode: 'partly-cloudy-day',
    humidity: 72,
    windSpeed: 24,
    windDirection: 'NW',
    visibility: 16,
    uvIndex: 4,
    pressure: 1013,
    sunrise: '06:14',
    sunset: '20:02',
    updatedAt: new Date().toISOString(),
  },
  forecast: [
    {
      date: '2026-06-19',
      dayLabel: 'Today',
      tempHigh: 20,
      tempLow: 13,
      condition: 'Partly Cloudy',
      conditionCode: 'partly-cloudy-day',
      precipChance: 15,
    },
    {
      date: '2026-06-20',
      dayLabel: 'Sat',
      tempHigh: 22,
      tempLow: 14,
      condition: 'Sunny',
      conditionCode: 'clear-day',
      precipChance: 5,
    },
    {
      date: '2026-06-21',
      dayLabel: 'Sun',
      tempHigh: 25,
      tempLow: 15,
      condition: 'Clear',
      conditionCode: 'clear-day',
      precipChance: 0,
    },
    {
      date: '2026-06-22',
      dayLabel: 'Mon',
      tempHigh: 19,
      tempLow: 13,
      condition: 'Cloudy',
      conditionCode: 'cloudy',
      precipChance: 30,
    },
    {
      date: '2026-06-23',
      dayLabel: 'Tue',
      tempHigh: 16,
      tempLow: 11,
      condition: 'Rain',
      conditionCode: 'rain',
      precipChance: 80,
    },
    {
      date: '2026-06-24',
      dayLabel: 'Wed',
      tempHigh: 14,
      tempLow: 10,
      condition: 'Drizzle',
      conditionCode: 'drizzle',
      precipChance: 60,
    },
    {
      date: '2026-06-25',
      dayLabel: 'Thu',
      tempHigh: 18,
      tempLow: 12,
      condition: 'Partly Cloudy',
      conditionCode: 'partly-cloudy-day',
      precipChance: 20,
    },
  ],
}