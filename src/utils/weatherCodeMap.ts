export interface WeatherInfo {
  label: string;
  emoji: string;
  icon: string;
}

const weatherCodeMap: Record<number, WeatherInfo> = {
  0:  { label: 'Clear Sky',            emoji: '☀️',  icon: 'clear' },
  1:  { label: 'Mainly Clear',         emoji: '🌤️',  icon: 'mainly-clear' },
  2:  { label: 'Partly Cloudy',        emoji: '⛅',  icon: 'partly-cloudy' },
  3:  { label: 'Overcast',             emoji: '☁️',  icon: 'overcast' },
  45: { label: 'Foggy',                emoji: '🌫️',  icon: 'fog' },
  48: { label: 'Icy Fog',              emoji: '🌫️',  icon: 'fog' },
  51: { label: 'Light Drizzle',        emoji: '🌦️',  icon: 'drizzle' },
  53: { label: 'Moderate Drizzle',     emoji: '🌦️',  icon: 'drizzle' },
  55: { label: 'Heavy Drizzle',        emoji: '🌧️',  icon: 'drizzle-heavy' },
  56: { label: 'Freezing Drizzle',     emoji: '🌨️',  icon: 'freezing-drizzle' },
  57: { label: 'Heavy Freezing Drizzle', emoji: '🌨️', icon: 'freezing-drizzle' },
  61: { label: 'Light Rain',           emoji: '🌧️',  icon: 'rain-light' },
  63: { label: 'Moderate Rain',        emoji: '🌧️',  icon: 'rain' },
  65: { label: 'Heavy Rain',           emoji: '🌧️',  icon: 'rain-heavy' },
  66: { label: 'Freezing Rain',        emoji: '🌨️',  icon: 'freezing-rain' },
  67: { label: 'Heavy Freezing Rain',  emoji: '🌨️',  icon: 'freezing-rain' },
  71: { label: 'Light Snow',           emoji: '🌨️',  icon: 'snow-light' },
  73: { label: 'Moderate Snow',        emoji: '❄️',  icon: 'snow' },
  75: { label: 'Heavy Snow',           emoji: '❄️',  icon: 'snow-heavy' },
  77: { label: 'Snow Grains',          emoji: '🌨️',  icon: 'snow-grains' },
  80: { label: 'Light Showers',        emoji: '🌦️',  icon: 'showers-light' },
  81: { label: 'Moderate Showers',     emoji: '🌧️',  icon: 'showers' },
  82: { label: 'Heavy Showers',        emoji: '🌧️',  icon: 'showers-heavy' },
  85: { label: 'Light Snow Showers',   emoji: '🌨️',  icon: 'snow-showers' },
  86: { label: 'Heavy Snow Showers',   emoji: '❄️',  icon: 'snow-showers-heavy' },
  95: { label: 'Thunderstorm',         emoji: '⛈️',  icon: 'thunderstorm' },
  96: { label: 'Thunderstorm w/ Hail', emoji: '⛈️',  icon: 'thunderstorm-hail' },
  99: { label: 'Thunderstorm w/ Heavy Hail', emoji: '⛈️', icon: 'thunderstorm-hail' },
};

export function getWeatherInfo(code: number): WeatherInfo {
  return weatherCodeMap[code] ?? { label: 'Unknown', emoji: '🌡️', icon: 'unknown' };
}

export default weatherCodeMap;