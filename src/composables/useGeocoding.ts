import { ref } from 'vue';
import { searchCity, type GeocodingResult } from '../services/geocodingService';

export function useGeocoding() {
  const result = ref<GeocodingResult | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function geocode(cityName: string): Promise<GeocodingResult | null> {
    loading.value = true;
    error.value = null;
    result.value = null;

    try {
      const geo = await searchCity(cityName);
      result.value = geo;
      return geo;
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'Failed to find city.';
      return null;
    } finally {
      loading.value = false;
    }
  }

  return { result, loading, error, geocode };
}