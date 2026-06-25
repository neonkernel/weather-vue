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
      const position = await getCurrentPosition()
      coords.value = position
      return position
    } catch (err: any) {
      if (
        err instanceof GeolocationPositionError &&
        err.code === GeolocationPositionError.PERMISSION_DENIED
      ) {
        permissionDenied.value = true
        error.value = 'Location permission denied.'
      } else if (
        err instanceof GeolocationPositionError &&
        err.code === GeolocationPositionError.TIMEOUT
      ) {
        error.value = 'Location request timed out.'
      } else if (!navigator.geolocation) {
        error.value = 'Geolocation is not supported by your browser.'
      } else {
        error.value = err?.message || 'Unable to retrieve location.'
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