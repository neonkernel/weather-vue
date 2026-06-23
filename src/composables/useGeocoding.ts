import { ref } from 'vue';
import { geocodeCity } from '../services/geocodingService';
import type { GeoLocation } from '../types/weather';

export function useGeocoding() {
  const location = ref<GeoLocation | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function resolveCity(cityName: string): Promise<GeoLocation | null> {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name.';
      return null;
    }

    loading.value = true;
    error.value = null;
    location.value = null;

    try {
      const result = await geocodeCity(cityName);
      location.value = result;
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to find the city.';
      return null;
    } finally {
      loading.value = false;
    }
  }

  function reset() {
    location.value = null;
    error.value = null;
    loading.value = false;
  }

  return { location, loading, error, resolveCity, reset };
}