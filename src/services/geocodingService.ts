import type { GeoLocation } from '../types/weather';

const GEOCODING_BASE_URL = 'https://geocoding-api.open-meteo.com/v1/search';

export interface GeocodingResult {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  country: string;
  country_code: string;
  admin1?: string;
}

export interface GeocodingResponse {
  results?: GeocodingResult[];
  error?: boolean;
  reason?: string;
}

/**
 * Search for a city by name and return geocoding results.
 */
export async function searchCity(cityName: string): Promise<GeocodingResult[]> {
  const params = new URLSearchParams({
    name: cityName.trim(),
    count: '5',
    language: 'en',
    format: 'json',
  });

  const response = await fetch(`${GEOCODING_BASE_URL}?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Geocoding API error: ${response.status} ${response.statusText}`);
  }

  const data: GeocodingResponse = await response.json();

  if (data.error) {
    throw new Error(data.reason ?? 'Geocoding API returned an error');
  }

  return data.results ?? [];
}

/**
 * Get the best matching GeoLocation for a city name string.
 */
export async function geocodeCity(cityName: string): Promise<GeoLocation> {
  const results = await searchCity(cityName);

  if (results.length === 0) {
    throw new Error(`City not found: "${cityName}". Please check the spelling and try again.`);
  }

  const best = results[0];
  const displayName = best.admin1
    ? `${best.name}, ${best.admin1}, ${best.country}`
    : `${best.name}, ${best.country}`;

  return {
    lat: best.latitude,
    lon: best.longitude,
    displayName,
    country: best.country,
    countryCode: best.country_code,
  };
}