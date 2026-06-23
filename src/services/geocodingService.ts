import type { GeoLocation } from '../types/weather';

const GEOCODING_BASE = 'https://geocoding-api.open-meteo.com/v1/search';

export interface GeocodeResult {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  country: string;
  country_code: string;
  admin1?: string;
}

export interface GeocodeResponse {
  results?: GeocodeResult[];
  generationtime_ms: number;
}

/**
 * Fetch geocoding results for a city name.
 * Returns up to `count` matches (default 5).
 */
export async function geocodeCity(cityName: string, count = 5): Promise<GeocodeResult[]> {
  if (!cityName.trim()) throw new Error('City name must not be empty.');

  const params = new URLSearchParams({
    name: cityName.trim(),
    count: String(count),
    language: 'en',
    format: 'json',
  });

  const response = await fetch(`${GEOCODING_BASE}?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Geocoding request failed: ${response.status} ${response.statusText}`);
  }

  const data: GeocodeResponse = await response.json();

  if (!data.results || data.results.length === 0) {
    throw new Error(`No location found for "${cityName}". Please check the spelling and try again.`);
  }

  return data.results;
}

/**
 * Resolve the first matching GeoLocation for a city name string.
 */
export async function resolveCity(cityName: string): Promise<GeoLocation> {
  const results = await geocodeCity(cityName, 1);
  const first = results[0];

  const displayParts = [first.name];
  if (first.admin1) displayParts.push(first.admin1);
  displayParts.push(first.country);

  return {
    lat: first.latitude,
    lon: first.longitude,
    displayName: displayParts.join(', '),
    country: first.country,
  };
}