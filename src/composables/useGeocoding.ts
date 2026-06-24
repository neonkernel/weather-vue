import { ref } from 'vue'
import { searchCity, type GeocodingResult } from '../services/geocodingService'

export function useGeocoding() {
  const results = ref<GeocodingResult[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function search(query: string) {
    if (!query.trim()) {
      results.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      results.value = await searchCity(query)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Search failed'
      results.value = []
    } finally {
      loading.value = false
    }
  }

  function clearResults() {
    results.value = []
  }

  return {
    results,
    loading,
    error,
    search,
    clearResults,
  }
}