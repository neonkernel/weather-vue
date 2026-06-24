const weatherCodeMap: Record<number, { description: string; emoji: string }> = {
  0: { description: 'Clear sky', emoji: '☀️' },
  1: { description: 'Mainly clear', emoji: '🌤️' },
  2: { description: 'Partly cloudy', emoji: '⛅' },
  3: { description: 'Overcast', emoji: '☁️' },
  45: { description: 'Foggy', emoji: '🌫️' },
  48: { description: 'Icy fog', emoji: '🌫️' },
  51: { description: 'Light drizzle', emoji: '🌦️' },
  53: { description: 'Drizzle', emoji: '🌦️' },
  55: { description: 'Heavy drizzle', emoji: '🌧️' },
  61: { description: 'Slight rain', emoji: '🌧️' },
  63: { description: 'Rain', emoji: '🌧️' },
  65: { description: 'Heavy rain', emoji: '🌧️' },
  71: { description: 'Slight snow', emoji: '🌨️' },
  73: { description: 'Snow', emoji: '❄️' },
  75: { description: 'Heavy snow', emoji: '❄️' },
  77: { description: 'Snow grains', emoji: '🌨️' },
  80: { description: 'Slight showers', emoji: '🌦️' },
  81: { description: 'Showers', emoji: '🌧️' },
  82: { description: 'Violent showers', emoji: '⛈️' },
  85: { description: 'Snow showers', emoji: '🌨️' },
  86: { description: 'Heavy snow showers', emoji: '❄️' },
  95: { description: 'Thunderstorm', emoji: '⛈️' },
  96: { description: 'Thunderstorm with hail', emoji: '⛈️' },
  99: { description: 'Thunderstorm with heavy hail', emoji: '⛈️' },
}

export function getWeatherDescription(code: number): string {
  return weatherCodeMap[code]?.description ?? 'Unknown'
}

export function getWeatherEmoji(code: number): string {
  return weatherCodeMap[code]?.emoji ?? '🌡️'
}