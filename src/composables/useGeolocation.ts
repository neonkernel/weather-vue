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
        reject(new Error('Geolocation is not supported by this browser.'))
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
      if (err && (err.code === 1 || err.code === GeolocationPositionError?.PERMISSION_DENIED)) {
        permissionDenied.value = true
        error.value = 'Location permission was denied.'
      } else if (err && err.code === 2) {
        error.value = 'Location is unavailable.'
      } else if (err && err.code === 3) {
        error.value = 'Location request timed out.'
      } else {
        error.value = err?.message || 'Failed to detect location.'
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { coords, loading, error, permissionDenied, detectLocation }
}