/**
 * Convert Celsius to Fahrenheit.
 */
export function celsiusToFahrenheit(celsius: number): number {
  return Math.round((celsius * 9) / 5 + 32);
}

/**
 * Convert metres-per-second to miles per hour.
 */
export function mpsToMph(mps: number): number {
  return Math.round(mps * 2.23694);
}

/**
 * Convert km/h to mph.
 */
export function kmhToMph(kmh: number): number {
  return Math.round(kmh * 0.621371);
}

/**
 * Format an ISO date string (YYYY-MM-DD) to a human-readable label.
 * @param isoDate  e.g. "2026-06-24"
 * @param options  Intl.DateTimeFormatOptions (defaults to weekday + month + day)
 */
export function formatDate(
  isoDate: string,
  options: Intl.DateTimeFormatOptions = { weekday: 'short', month: 'short', day: 'numeric' }
): string {
  // Parse as UTC noon to avoid timezone-shift issues
  const date = new Date(`${isoDate}T12:00:00Z`);
  return date.toLocaleDateString('en-US', { ...options, timeZone: 'UTC' });
}

/**
 * Returns "Today", "Tomorrow", or a formatted date string.
 */
export function friendlyDate(isoDate: string): string {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const tomorrowDate = new Date(today);
  tomorrowDate.setDate(today.getDate() + 1);
  const tomorrowStr = tomorrowDate.toISOString().slice(0, 10);

  if (isoDate === todayStr) return 'Today';
  if (isoDate === tomorrowStr) return 'Tomorrow';
  return formatDate(isoDate, { weekday: 'short', month: 'short', day: 'numeric' });
}