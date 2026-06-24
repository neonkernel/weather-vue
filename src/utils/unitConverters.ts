export function celsiusToFahrenheit(celsius: number): number {
  return (celsius * 9) / 5 + 32
}

export function fahrenheitToCelsius(fahrenheit: number): number {
  return ((fahrenheit - 32) * 5) / 9
}

export function kmhToMph(kmh: number): number {
  return kmh * 0.621371
}

export function mphToKmh(mph: number): number {
  return mph / 0.621371
}

export function mmToInches(mm: number): number {
  return mm * 0.0393701
}