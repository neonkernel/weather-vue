export interface WeatherCodeInfo {
  label: string
  emoji: string
  icon: string
}

const weatherCodeMap: Record<number, WeatherCodeInfo> = {
  0: { label: 'Clear Sky', emoji: '☀️', icon: 'clear' },
  1: { label: 'Mainly Clear', emoji: '🌤️', icon: 'mostly-clear' },
  2: { label: 'Partly Cloudy', emoji: '⛅', icon: 'partly-cloudy' },
  3: { label: 'Overcast', emoji: '☁️', icon: 'overcast' },
  45: { label: 'Foggy', emoji: '🌫️', icon: 'fog' },
  48: { label: 'Icy Fog', emoji: '🌫️', icon: 'fog' },
  51: { label: 'Light Drizzle', emoji: '🌦️', icon: 'drizzle' },
  53: { label: 'Moderate Drizzle', emoji: '🌦️', icon: 'drizzle' },
  55: { label: 'Dense Drizzle', emoji: '🌧️', icon: 'drizzle' },
  56: { label: 'Freezing Drizzle', emoji: '🌨️', icon: 'freezing-drizzle' },
  57: { label: 'Heavy Freezing Drizzle', emoji: '🌨️', icon: 'freezing-drizzle' },
  61: { label: 'Slight Rain', emoji: '🌧️', icon: 'rain' },
  63: { label: 'Moderate Rain', emoji: '🌧️', icon: 'rain' },
  65: { label: 'Heavy Rain', emoji: '🌧️', icon: 'heavy-rain' },
  66: { label: 'Freezing Rain', emoji: '🌨️', icon: 'freezing-rain' },
  67: { label: 'Heavy Freezing Rain', emoji: '🌨️', icon: 'freezing-rain' },
  71: { label: 'Slight Snowfall', emoji: '🌨️', icon: 'snow' },
  73: { label: 'Moderate Snowfall', emoji: '❄️', icon: 'snow' },
  75: { label: 'Heavy Snowfall', emoji: '❄️', icon: 'heavy-snow' },
  77: { label: 'Snow Grains', emoji: '🌨️', icon: 'snow-grains' },
  80: { label: 'Slight Showers', emoji: '🌦️', icon: 'showers' },
  81: { label: 'Moderate Showers', emoji: '🌧️', icon: 'showers' },
  82: { label: 'Violent Showers', emoji: '⛈️', icon: 'heavy-showers' },
  85: { label: 'Slight Snow Showers', emoji: '🌨️', icon: 'snow-showers' },
  86: { label: 'Heavy Snow Showers', emoji: '❄️', icon: 'snow-showers' },
  95: { label: 'Thunderstorm', emoji: '⛈️', icon: 'thunderstorm' },
  96: { label: 'Thunderstorm w/ Hail', emoji: '⛈️', icon: 'thunderstorm-hail' },
  99: { label: 'Thunderstorm w/ Heavy Hail', emoji: '⛈️', icon: 'thunderstorm-hail' },
}

export function getWeatherInfo(code: number): WeatherCodeInfo {
  return weatherCodeMap[code] ?? { label: 'Unknown', emoji: '🌡️', icon: 'unknown' }
}

export default weatherCodeMap