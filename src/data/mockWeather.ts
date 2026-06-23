// Mock data kept for reference / testing purposes
// The app now uses live API data via useWeatherApi composable

import type { WeatherData } from '../types/weather'

export const mockWeatherData: WeatherData = {
  city: 'London, England',
  country: 'United Kingdom',
  lastUpdated: new Date().toISOString(),
  current: {
    temperature: 14,
    feelsLike: 11,
    humidity: 78,
    windSpeed: 22,
    windDirection: 245,
    weatherCode: 61,
    weatherLabel: 'Slight Rain',
    weatherEmoji: '🌧️',
    isDay: true,
    uvIndex: 2,
    visibility: 10,
    precipitation: 1.2,
  },
  forecast: [
    {
      date: '2024-01-15',
      dateFormatted: 'Today',
      tempMax: 14,
      tempMin: 8,
      weatherCode: 61,
      weatherLabel: 'Slight Rain',
      weatherEmoji: '🌧️',
      precipitationSum: 3.2,
      windSpeedMax: 28,
      uvIndexMax: 2,
    },
    {
      date: '2024-01-16',
      dateFormatted: 'Tomorrow',
      tempMax: 12,
      tempMin: 6,
      weatherCode: 3,
      weatherLabel: 'Overcast',
      weatherEmoji: '☁️',
      precipitationSum: 0,
      windSpeedMax: 20,
      uvIndexMax: 1,
    },
    {
      date: '2024-01-17',
      dateFormatted: 'Wed, Jan 17',
      tempMax: 16,
      tempMin: 9,
      weatherCode: 1,
      weatherLabel: 'Mainly Clear',
      weatherEmoji: '🌤️',
      precipitationSum: 0,
      windSpeedMax: 15,
      uvIndexMax: 3,
    },
  ],
}