export interface WeatherCodeInfo {
  label: string;
  emoji: string;
  icon: string;
}

const weatherCodeMap: Record<number, WeatherCodeInfo> = {
  0:  { label: 'Clear Sky',            emoji: '☀️',  icon: 'sunny' },
  1:  { label: 'Mainly Clear',         emoji: '🌤️', icon: 'partly-cloudy' },
  2:  { label: 'Partly Cloudy',        emoji: '⛅',  icon: 'partly-cloudy' },
  3:  { label: 'Overcast',             emoji: '☁️',  icon: 'cloudy' },
  45: { label: 'Foggy',                emoji: '🌫️', icon: 'fog' },
  48: { label: 'Icy Fog',              emoji: '🌫️', icon: 'fog' },
  51: { label: 'Light Drizzle',        emoji: '🌦️', icon: 'drizzle' },
  53: { label: 'Moderate Drizzle',     emoji: '🌦️', icon: 'drizzle' },
  55: { label: 'Dense Drizzle',        emoji: '🌧️', icon: 'drizzle' },
  56: { label: 'Light Freezing Drizzle', emoji: '🌨️', icon: 'sleet' },
  57: { label: 'Heavy Freezing Drizzle', emoji: '🌨️', icon: 'sleet' },
  61: { label: 'Slight Rain',          emoji: '🌧️', icon: 'rain' },
  63: { label: 'Moderate Rain',        emoji: '🌧️', icon: 'rain' },
  65: { label: 'Heavy Rain',           emoji: '🌧️', icon: 'rain' },
  66: { label: 'Light Freezing Rain',  emoji: '🌨️', icon: 'sleet' },
  67: { label: 'Heavy Freezing Rain',  emoji: '🌨️', icon: 'sleet' },
  71: { label: 'Slight Snowfall',      emoji: '🌨️', icon: 'snow' },
  73: { label: 'Moderate Snowfall',    emoji: '❄️',  icon: 'snow' },
  75: { label: 'Heavy Snowfall',       emoji: '❄️',  icon: 'snow' },
  77: { label: 'Snow Grains',          emoji: '🌨️', icon: 'snow' },
  80: { label: 'Slight Rain Showers',  emoji: '🌦️', icon: 'showers' },
  81: { label: 'Moderate Rain Showers',emoji: '🌧️', icon: 'showers' },
  82: { label: 'Violent Rain Showers', emoji: '⛈️',  icon: 'showers' },
  85: { label: 'Slight Snow Showers',  emoji: '🌨️', icon: 'snow-showers' },
  86: { label: 'Heavy Snow Showers',   emoji: '❄️',  icon: 'snow-showers' },
  95: { label: 'Thunderstorm',         emoji: '⛈️',  icon: 'thunderstorm' },
  96: { label: 'Thunderstorm w/ Hail', emoji: '⛈️',  icon: 'thunderstorm' },
  99: { label: 'Thunderstorm w/ Heavy Hail', emoji: '⛈️', icon: 'thunderstorm' },
};

export function getWeatherInfo(code: number): WeatherCodeInfo {
  return weatherCodeMap[code] ?? { label: 'Unknown', emoji: '🌡️', icon: 'unknown' };
}

export default weatherCodeMap;