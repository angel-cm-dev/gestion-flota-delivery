import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

/**
 * Carga datos asíncronos con estados de carga/error y recarga manual.
 * Ignora respuestas de peticiones viejas (evita "condiciones de carrera" al
 * escribir rápido en un buscador).
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const callId = useRef(0);

  const run = useCallback(() => {
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    fn()
      .then((d) => id === callId.current && setData(d))
      .catch((e: unknown) => id === callId.current && setError(e instanceof ApiError ? e.message : 'Error inesperado'))
      .finally(() => id === callId.current && setLoading(false));
    // `deps` lo define quien llama (igual que en useEffect).
  }, deps);

  useEffect(run, [run]);
  return { data, loading, error, reload: run, setData };
}

export function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
