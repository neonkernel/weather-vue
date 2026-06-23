import { ref } from 'vue';
import { searchCity } from '../services/geocodingService';
import { fetchWeatherByCoords, type WeatherApiResponse } from '../services/weatherService';

export interface WeatherState {
  data: WeatherApiResponse | null;
  cityName: string;
  loading: boolean;
  error: string | null;
}

export function useWeatherApi() {
  const data = ref<WeatherApiResponse | null>(null);
  const cityName = ref<string>('');
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchByCity(name: string): Promise<void> {
    if (!name.trim()) {
      error.value = 'Please enter a city name.';
      return;
    }

    loading.value = true;
    error.value = null;
    data.value = null;

    try {
      // Step 1: Geocode city → lat/lon
      const geo = await searchCity(name.trim());

      // Step 2: Fetch weather using coordinates
      const weather = await fetchWeatherByCoords(geo.lat, geo.lon);

      cityName.value = geo.displayName;
      data.value = weather;
    } catch (err: unknown) {
      error.value =
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred. Please try again.';
    } finally {
      loading.value = false;
    }
  }

  return { data, cityName, loading, error, fetchByCity };
}