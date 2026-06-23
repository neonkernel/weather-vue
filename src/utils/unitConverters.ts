/**
 * Convert Celsius to Fahrenheit
 */
export function celsiusToFahrenheit(celsius: number): number {
  return Math.round((celsius * 9) / 5 + 32)
}

/**
 * Convert meters per second to miles per hour
 */
export function mpsToMph(mps: number): number {
  return Math.round(mps * 2.237)
}

/**
 * Convert km/h to mph
 */
export function kphToMph(kph: number): number {
  return Math.round(kph * 0.621371)
}

/**
 * Format an ISO date string to a human-readable label
 * e.g. "2024-01-15" → "Mon, Jan 15"
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Returns "Today", "Tomorrow", or a formatted date
 */
export function formatDateRelative(dateStr: string): string {
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const date = new Date(dateStr + 'T00:00:00')

  if (date.toDateString() === today.toDateString()) return 'Today'
  if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return formatDate(dateStr)
}

/**
 * Format a timestamp string to a readable time
 */
export function formatTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}