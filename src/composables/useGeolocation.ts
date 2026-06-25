import { ref } from 'vue'

export interface GeolocationResult {
  lat: number
  lon: number
}

export function useGeolocation() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const permissionDenied = ref(false)
  const coords = ref<GeolocationResult | null>(null)

  function getPosition(): Promise<GeolocationResult> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by this browser.'))
        return
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          })
        },
        (err) => {
          reject(err)
        },
        {
          enableHighAccuracy: false,
          timeout: 10000,
          maximumAge: 300000,
        }
      )
    })
  }

  async function detectLocation(): Promise<GeolocationResult | null> {
    loading.value = true
    error.value = null
    permissionDenied.value = false
    coords.value = null

    try {
      const result = await getPosition()
      coords.value = result
      return result
    } catch (err: any) {
      if (err.code === 1) {
        // PERMISSION_DENIED
        permissionDenied.value = true
        error.value = 'Location permission denied.'
      } else if (err.code === 2) {
        // POSITION_UNAVAILABLE
        error.value = 'Location unavailable.'
      } else if (err.code === 3) {
        // TIMEOUT
        error.value = 'Location request timed out.'
      } else {
        error.value = err.message || 'Failed to get location.'
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    coords,
    loading,
    error,
    permissionDenied,
    detectLocation,
  }
}