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

  function setLocation(payload: {
    lat: number
    lon: number
    cityName: string
    source: LocationSource
  }) {
    lat.value = payload.lat
    lon.value = payload.lon
    cityName.value = payload.cityName
    source.value = payload.source
  }

  function setDefaultLocation() {
    lat.value = 40.7128
    lon.value = -74.006
    cityName.value = 'New York'
    source.value = 'default'
  }

  function setCityName(name: string) {
    cityName.value = name
  }

  return {
    lat,
    lon,
    cityName,
    source,
    setLocation,
    setDefaultLocation,
    setCityName,
  }
})