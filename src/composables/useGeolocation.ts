import { ref } from 'vue'

export interface GeolocationCoords {
  lat: number
  lon: number
}

export interface UseGeolocationReturn {
  coords: ReturnType<typeof ref<GeolocationCoords | null>>
  loading: ReturnType<typeof ref<boolean>>
  error: ReturnType<typeof ref<string | null>>
  permissionDenied: ReturnType<typeof ref<boolean>>
  getCurrentLocation: () => Promise<GeolocationCoords | null>
}

export function useGeolocation() {
  const coords = ref<GeolocationCoords | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const permissionDenied = ref(false)

  function getCurrentLocation(): Promise<GeolocationCoords | null> {
    if (!navigator.geolocation) {
      error.value = 'Geolocation is not supported by your browser.'
      permissionDenied.value = false
      return Promise.resolve(null)
    }

    loading.value = true
    error.value = null
    permissionDenied.value = false

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const result: GeolocationCoords = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
          }
          coords.value = result
          loading.value = false
          resolve(result)
        },
        (err) => {
          loading.value = false
          if (err.code === GeolocationPositionError.PERMISSION_DENIED) {
            permissionDenied.value = true
            error.value = 'Location permission denied.'
          } else if (err.code === GeolocationPositionError.POSITION_UNAVAILABLE) {
            error.value = 'Location information is unavailable.'
          } else if (err.code === GeolocationPositionError.TIMEOUT) {
            error.value = 'The request to get your location timed out.'
          } else {
            error.value = 'An unknown error occurred while retrieving location.'
          }
          resolve(null)
        },
        {
          enableHighAccuracy: false,
          timeout: 10000,
          maximumAge: 300000, // 5 minutes cache
        }
      )
    })
  }

  return {
    coords,
    loading,
    error,
    permissionDenied,
    getCurrentLocation,
  }
}