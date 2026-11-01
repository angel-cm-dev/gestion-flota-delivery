// Validaciones del lado del cliente. Replican las reglas del backend para dar
// feedback inmediato, pero el backend sigue siendo la fuente de verdad.

const CAR = /^([A-Z][A-Z0-9]{2})-?(\d{3})$/;
const MOTO = /^(\d{4})-?([A-Z]{2})$/;

/** Normaliza una placa peruana (ABC-123 / 1234-AB). Devuelve null si es inválida. */
export function normalizePlate(raw: string): string | null {
  const v = raw.replace(/\s+/g, '').toUpperCase();
  const car = CAR.exec(v);
  if (car) return `${car[1]}-${car[2]}`;
  const moto = MOTO.exec(v);
  if (moto) return `${moto[1]}-${moto[2]}`;
  return null;
}

export const isDni = (v: string) => /^\d{8}$/.test(v);
export const isMobilePe = (v: string) => /^9\d{8}$/.test(v);
export const isLicenseNumber = (v: string) => /^[A-Z]\d{8}$/.test(v.trim().toUpperCase());
export const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

export function passwordIssues(pwd: string): string[] {
  const issues: string[] = [];
  if (pwd.length < 8) issues.push('mínimo 8 caracteres');
  if (!/[A-Z]/.test(pwd)) issues.push('una mayúscula');
  if (!/[a-z]/.test(pwd)) issues.push('una minúscula');
  if (!/\d/.test(pwd)) issues.push('un número');
  return issues;
}

/** Coordenadas dentro del rectángulo aproximado de Perú (detecta lat/lng invertidas). */
export function isInPeru(lat: number, lng: number): boolean {
  return lat >= -18.4 && lat <= 0.1 && lng >= -81.4 && lng <= -68.6;
}

export type Validator<T> = (values: T) => Partial<Record<keyof T, string>>;

/** Ejecuta un validador y devuelve true si no hay errores. */
export function isValid<T>(errors: Partial<Record<keyof T, string>>): boolean {
  return Object.values(errors).every((e) => !e);
}
