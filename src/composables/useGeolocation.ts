import { ref } from 'vue'

export interface GeolocationCoords {
  latitude: number
  longitude: number
}

export function useGeolocation() {
  const coords = ref<GeolocationCoords | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const permissionDenied = ref(false)

  function getCurrentPosition(): Promise<GeolocationCoords> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by your browser.'))
        return
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          })
        },
        (err) => {
          reject(err)
        },
        {
          timeout: 10000,
          maximumAge: 300000,
          enableHighAccuracy: false,
        }
      )
    })
  }

  async function detectLocation(): Promise<GeolocationCoords | null> {
    loading.value = true
    error.value = null
    permissionDenied.value = false
    coords.value = null

    try {
      const result = await getCurrentPosition()
      coords.value = result
      return result
    } catch (err: any) {
      if (err?.code === 1) {
        // PERMISSION_DENIED
        permissionDenied.value = true
        error.value = 'Location permission was denied.'
      } else if (err?.code === 2) {
        // POSITION_UNAVAILABLE
        error.value = 'Location information is unavailable.'
      } else if (err?.code === 3) {
        // TIMEOUT
        error.value = 'The request to get your location timed out.'
      } else {
        error.value = err?.message || 'Unable to retrieve your location.'
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