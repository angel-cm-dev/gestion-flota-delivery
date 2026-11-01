import { daysLabel, formatDate, formatKm, todayLima } from './format';
import { statusInfo } from './status';
import { isDni, isInPeru, isLicenseNumber, isMobilePe, normalizePlate, passwordIssues } from './validation';

describe('normalizePlate', () => {
  it.each([
    ['abc123', 'ABC-123'],
    [' a1b 234 ', 'A1B-234'],
    ['4521lm', '4521-LM'],
    ['C4F-512', 'C4F-512'],
  ])('normaliza %s -> %s', (raw, expected) => {
    expect(normalizePlate(raw)).toBe(expected);
  });

  it.each(['AB-123', '1BC-123', 'ABC-12', '45-LM', ''])('rechaza %s', (raw) => {
    expect(normalizePlate(raw)).toBeNull();
  });
});

describe('validaciones peruanas', () => {
  it('valida DNI, celular y licencia', () => {
    expect(isDni('45781236')).toBe(true);
    expect(isDni('4578123')).toBe(false);
    expect(isMobilePe('987654321')).toBe(true);
    expect(isMobilePe('187654321')).toBe(false);
    expect(isLicenseNumber('q45781236')).toBe(true);
    expect(isLicenseNumber('45781236')).toBe(false);
  });

  it('detecta coordenadas fuera de Perú (lat/lng invertidas)', () => {
    expect(isInPeru(-12.05, -77.04)).toBe(true);
    expect(isInPeru(-77.04, -12.05)).toBe(false);
  });

  it('lista lo que le falta a una contraseña', () => {
    expect(passwordIssues('Demo123!')).toEqual([]);
    expect(passwordIssues('abc')).toEqual(['mínimo 8 caracteres', 'una mayúscula', 'un número']);
  });
});

describe('formato', () => {
  it('formatea fechas ISO sin desfase de zona horaria', () => {
    expect(formatDate('2026-06-15')).toBe('15/06/2026');
    expect(formatDate(null)).toBe('—');
  });

  it('calcula "hoy" en hora de Lima (UTC-5)', () => {
    // 03:00 UTC del 16 de junio todavía es 15 de junio en Lima.
    expect(todayLima(new Date('2026-06-16T03:00:00Z'))).toBe('2026-06-15');
    expect(todayLima(new Date('2026-06-16T06:00:00Z'))).toBe('2026-06-16');
  });

  it('describe días restantes', () => {
    expect(daysLabel(-3)).toBe('vencido hace 3 d');
    expect(daysLabel(0)).toBe('vence hoy');
    expect(daysLabel(12)).toBe('en 12 d');
    expect(formatKm(1500)).toMatch(/1[.,\s]?500 km/);
  });

  it('traduce estados a etiqueta y tono', () => {
    expect(statusInfo('por_vencer')).toEqual({ label: 'Por vencer', tone: 'amber' });
    expect(statusInfo('desconocido_x').label).toBe('desconocido x');
  });
});
