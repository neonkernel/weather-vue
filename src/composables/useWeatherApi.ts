import { ref } from 'vue';
import { resolveCity } from '../services/geocodingService';
import { fetchWeatherForLocation } from '../services/weatherService';
import type { WeatherData } from '../types/weather';

export function useWeatherApi() {
  const data = ref<WeatherData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Fetch weather by city name string.
   * Handles geocoding → weather fetch in one call.
   */
  async function fetchByCity(cityName: string) {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name.';
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      const location = await resolveCity(cityName);
      data.value = await fetchWeatherForLocation(location);
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred while fetching weather data.';
      data.value = null;
    } finally {
      loading.value = false;
    }
  }

  function clearError() {
    error.value = null;
  }

  function reset() {
    data.value = null;
    error.value = null;
    loading.value = false;
  }

  return { data, loading, error, fetchByCity, clearError, reset };
}