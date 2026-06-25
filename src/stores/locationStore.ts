import { defineStore } from 'pinia'
import { ref } from 'vue'

export type LocationSource = 'geo' | 'search' | 'default'

export interface LocationState {
  lat: number | null
  lon: number | null
  cityName: string
  source: LocationSource
}

export const useLocationStore = defineStore('location', () => {
  const lat = ref<number | null>(null)
  const lon = ref<number | null>(null)
  const cityName = ref<string>('')
  const source = ref<LocationSource>('default')

  function setLocation(payload: LocationState) {
    lat.value = payload.lat
    lon.value = payload.lon
    cityName.value = payload.cityName
    source.value = payload.source
  }

  function clearLocation() {
    lat.value = null
    lon.value = null
    cityName.value = ''
    source.value = 'default'
  }

  return {
    lat,
    lon,
    cityName,
    source,
    setLocation,
    clearLocation,
  }
})