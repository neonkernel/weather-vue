export interface GeocodingResult {
  lat: number;
  lon: number;
  displayName: string;
  country: string;
  admin1?: string;
}

const GEOCODING_BASE_URL = 'https://geocoding-api.open-meteo.com/v1';

export async function searchCity(cityName: string): Promise<GeocodingResult> {
  const params = new URLSearchParams({
    name: cityName,
    count: '1',
    language: 'en',
    format: 'json',
  });

  const response = await fetch(`${GEOCODING_BASE_URL}/search?${params}`);

  if (!response.ok) {
    throw new Error(`Geocoding API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  if (!data.results || data.results.length === 0) {
    throw new Error(`City not found: "${cityName}". Please check the spelling and try again.`);
  }

  const result = data.results[0];
  const parts = [result.name, result.admin1, result.country].filter(Boolean);

  return {
    lat: result.latitude,
    lon: result.longitude,
    displayName: parts.join(', '),
    country: result.country ?? '',
    admin1: result.admin1,
  };
}