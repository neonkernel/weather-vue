import { ref } from 'vue';
import { geocodeCity } from '../services/geocodingService';
import {
  fetchWeatherData,
  transformCurrentWeather,
  transformForecast,
} from '../services/weatherService';
import type { WeatherData } from '../types/weather';

export function useWeatherApi() {
  const data = ref<WeatherData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchByCity(cityName: string): Promise<void> {
    if (!cityName.trim()) {
      error.value = 'Please enter a city name.';
      return;
    }

    loading.value = true;
    error.value = null;
    data.value = null;

    try {
      // Step 1: Geocode the city name to lat/lon
      const location = await geocodeCity(cityName);

      // Step 2: Fetch weather data for that location
      const raw = await fetchWeatherData(location.lat, location.lon);

      // Step 3: Transform and store
      const current = transformCurrentWeather(raw);

      // Inject UV index from daily data (first day = today)
      if (raw.daily.uv_index_max && raw.daily.uv_index_max.length > 0) {
        current.uvIndex = raw.daily.uv_index_max[0] ?? 0;
      }

      const forecast = transformForecast(raw);

      data.value = {
        location,
        current,
        forecast,
        timezone: raw.timezone,
        fetchedAt: new Date(),
      };
    } catch (err) {
      error.value =
        err instanceof Error
          ? err.message
          : 'An unexpected error occurred while fetching weather data.';
    } finally {
      loading.value = false;
    }
  }

  function reset() {
    data.value = null;
    error.value = null;
    loading.value = false;
  }

  return { data, loading, error, fetchByCity, reset };
}