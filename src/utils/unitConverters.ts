/**
 * Convert Celsius to Fahrenheit
 */
export function celsiusToFahrenheit(celsius: number): number {
  return Math.round((celsius * 9) / 5 + 32);
}

/**
 * Convert meters per second to miles per hour
 */
export function mpsToMph(mps: number): number {
  return Math.round(mps * 2.23694);
}

/**
 * Convert km/h to mph
 */
export function kmhToMph(kmh: number): number {
  return Math.round(kmh * 0.621371);
}

/**
 * Format an ISO date string into a human-readable short date (e.g. "Mon, Jun 23")
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a number with one decimal place
 */
export function toOneDecimal(value: number): number {
  return Math.round(value * 10) / 10;
}