export interface WeatherInfo {
  label: string;
  emoji: string;
  icon: string; // icon name / identifier
}

/**
 * Maps WMO Weather Interpretation Codes (WW) to human-readable labels and emoji.
 * Reference: https://open-meteo.com/en/docs#weathervariables
 */
const weatherCodeMap: Record<number, WeatherInfo> = {
  0:  { label: 'Clear Sky',               emoji: '☀️',  icon: 'clear-day' },
  1:  { label: 'Mainly Clear',            emoji: '🌤️', icon: 'partly-cloudy-day' },
  2:  { label: 'Partly Cloudy',           emoji: '⛅',  icon: 'partly-cloudy-day' },
  3:  { label: 'Overcast',               emoji: '☁️',  icon: 'cloudy' },
  45: { label: 'Foggy',                  emoji: '🌫️', icon: 'fog' },
  48: { label: 'Icy Fog',               emoji: '🌫️', icon: 'fog' },
  51: { label: 'Light Drizzle',          emoji: '🌦️', icon: 'drizzle' },
  53: { label: 'Moderate Drizzle',       emoji: '🌦️', icon: 'drizzle' },
  55: { label: 'Dense Drizzle',          emoji: '🌧️', icon: 'drizzle' },
  56: { label: 'Light Freezing Drizzle', emoji: '🌨️', icon: 'sleet' },
  57: { label: 'Heavy Freezing Drizzle', emoji: '🌨️', icon: 'sleet' },
  61: { label: 'Slight Rain',            emoji: '🌧️', icon: 'rain' },
  63: { label: 'Moderate Rain',          emoji: '🌧️', icon: 'rain' },
  65: { label: 'Heavy Rain',             emoji: '🌧️', icon: 'rain' },
  66: { label: 'Light Freezing Rain',    emoji: '🌨️', icon: 'sleet' },
  67: { label: 'Heavy Freezing Rain',    emoji: '🌨️', icon: 'sleet' },
  71: { label: 'Slight Snowfall',        emoji: '🌨️', icon: 'snow' },
  73: { label: 'Moderate Snowfall',      emoji: '❄️',  icon: 'snow' },
  75: { label: 'Heavy Snowfall',         emoji: '❄️',  icon: 'snow' },
  77: { label: 'Snow Grains',            emoji: '🌨️', icon: 'snow' },
  80: { label: 'Slight Showers',         emoji: '🌦️', icon: 'showers-day' },
  81: { label: 'Moderate Showers',       emoji: '🌧️', icon: 'showers-day' },
  82: { label: 'Violent Showers',        emoji: '⛈️',  icon: 'showers-day' },
  85: { label: 'Slight Snow Showers',    emoji: '🌨️', icon: 'snow' },
  86: { label: 'Heavy Snow Showers',     emoji: '❄️',  icon: 'snow' },
  95: { label: 'Thunderstorm',           emoji: '⛈️',  icon: 'thunderstorms' },
  96: { label: 'Thunderstorm w/ Hail',   emoji: '⛈️',  icon: 'thunderstorms' },
  99: { label: 'Thunderstorm w/ Heavy Hail', emoji: '⛈️', icon: 'thunderstorms' },
};

export function getWeatherInfo(code: number): WeatherInfo {
  return weatherCodeMap[code] ?? { label: 'Unknown', emoji: '🌡️', icon: 'thermometer' };
}

export default weatherCodeMap;