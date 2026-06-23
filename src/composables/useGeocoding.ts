import { ref } from 'vue';
import { resolveCity } from '../services/geocodingService';
import type { GeoLocation } from '../types/weather';

export function useGeocoding() {
  const location = ref<GeoLocation | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function geocode(cityName: string) {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name.';
      return;
    }

    loading.value = true;
    error.value = null;
    location.value = null;

    try {
      location.value = await resolveCity(cityName);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to find location.';
    } finally {
      loading.value = false;
    }
  }

  return { location, loading, error, geocode };
}