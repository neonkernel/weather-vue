export interface GeoLocation {
  lat: number;
  lon: number;
  displayName: string;
  country: string;
  countryCode: string;
}

export interface WeatherCurrent {
  temperature: number;       // °C
  feelsLike: number;         // °C
  humidity: number;          // %
  windSpeed: number;         // km/h
  windDirection: number;     // degrees
  weatherCode: number;       // WMO code
  isDay: number;             // 1 = day, 0 = night
  precipitation: number;     // mm
  uvIndex: number;
}

export interface ForecastDay {
  date: string;              // ISO date string e.g. "2026-06-23"
  temperatureMax: number;    // °C
  temperatureMin: number;    // °C
  precipitationSum: number;  // mm
  windSpeedMax: number;      // km/h
  weatherCode: number;       // WMO code
  uvIndexMax: number;
}

export interface WeatherData {
  location: GeoLocation;
  current: WeatherCurrent;
  forecast: ForecastDay[];
  timezone: string;
  fetchedAt: Date;
}