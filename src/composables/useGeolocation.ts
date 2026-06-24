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

  async function getCurrentPosition(): Promise<GeolocationCoords | null> {
    if (!navigator.geolocation) {
      error.value = 'Geolocation is not supported by your browser.'
      return null
    }

    loading.value = true
    error.value = null
    permissionDenied.value = false
    coords.value = null

    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          timeout: 10000,
          maximumAge: 300000,
          enableHighAccuracy: false,
        })
      })

      coords.value = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      }
      return coords.value
    } catch (err: unknown) {
      const geoError = err as GeolocationPositionError
      if (geoError.code === GeolocationPositionError.PERMISSION_DENIED) {
        permissionDenied.value = true
        error.value = 'Location permission was denied.'
      } else if (geoError.code === GeolocationPositionError.POSITION_UNAVAILABLE) {
        error.value = 'Location information is unavailable.'
      } else if (geoError.code === GeolocationPositionError.TIMEOUT) {
        error.value = 'Location request timed out.'
      } else {
        error.value = 'An unknown error occurred while retrieving location.'
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
    getCurrentPosition,
  }
}