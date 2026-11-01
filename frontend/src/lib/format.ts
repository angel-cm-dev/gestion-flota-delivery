const pen = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' });
const num = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 });

export const formatMoney = (value: number) => pen.format(value);
export const formatNumber = (value: number) => num.format(value);
export const formatKm = (value: number) => `${num.format(value)} km`;
export const formatKg = (value: number) => `${num.format(value)} kg`;

/** "2026-06-15" -> "15/06/2026" sin pasar por Date (evita desfases de zona horaria). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' });
}

/** Fecha de hoy en Lima en formato ISO (YYYY-MM-DD). */
export function todayLima(now: Date = new Date()): string {
  // Perú es UTC-5 todo el año (sin horario de verano).
  const lima = new Date(now.getTime() - 5 * 60 * 60 * 1000);
  return lima.toISOString().slice(0, 10);
}

export function daysLabel(days: number): string {
  if (days < 0) return `vencido hace ${-days} d`;
  if (days === 0) return 'vence hoy';
  return `en ${days} d`;
}
