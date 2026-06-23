export interface GeoLocation {
  lat: number;
  lon: number;
  displayName: string;
  country: string;
}

export interface WeatherCurrent {
  temperature: number;
  feelsLike: number;
  humidity: number;
  windSpeed: number;
  windDirection: number;
  weatherCode: number;
  weatherLabel: string;
  weatherEmoji: string;
  isDay: boolean;
  precipitationProbability: number;
  uvIndex: number;
}

export interface ForecastDay {
  date: string;
  dateFormatted: string;
  tempMax: number;
  tempMin: number;
  weatherCode: number;
  weatherLabel: string;
  weatherEmoji: string;
  precipitationSum: number;
  precipitationProbability: number;
  windSpeedMax: number;
  uvIndexMax: number;
}

export interface WeatherData {
  location: GeoLocation;
  current: WeatherCurrent;
  forecast: ForecastDay[];
  fetchedAt: string;
}