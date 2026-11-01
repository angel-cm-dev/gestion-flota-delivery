// Cliente HTTP mínimo sobre fetch.
// - Adjunta el token JWT en cada petición.
// - Convierte las respuestas ProblemDetails del backend en ApiError tipado.
// - Ante un 401 emite un evento global para que la app cierre la sesión.

const TOKEN_KEY = 'flota.token';
export const UNAUTHORIZED_EVENT = 'flota:unauthorized';

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public errors: FieldError[] = [],
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** Mensaje de error por campo, útil para pintar bajo cada input. */
  fieldErrors(): Record<string, string> {
    return Object.fromEntries(this.errors.map((e) => [e.field, e.message]));
  }
}

export const tokenStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export async function parseError(res: Response): Promise<ApiError> {
  let body: { detail?: unknown; code?: string; errors?: FieldError[]; title?: string } = {};
  try {
    body = await res.json();
  } catch {
    /* respuesta sin JSON (p. ej. 502 del proxy) */
  }
  const detail = typeof body.detail === 'string' ? body.detail : body.title;
  const fallback = res.status >= 500 ? 'Error del servidor. Intenta nuevamente.' : `Error ${res.status}`;
  return new ApiError(res.status, detail || fallback, body.code, Array.isArray(body.errors) ? body.errors : []);
}

type Query = Record<string, string | number | boolean | null | undefined>;

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v));
  });
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

async function request<T>(method: string, path: string, opts: { body?: unknown; query?: Query; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form; // el navegador agrega el boundary de multipart
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), { method, headers, body });
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor. Revisa tu conexión.', 'network_error');
  }
  if (res.status === 401 && token) {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
  del: (path: string) => request<void>('DELETE', path),
  postForm: <T>(path: string, form: FormData) => request<T>('POST', path, { form }),
  /** Descarga un recurso protegido (p. ej. una foto) como URL de objeto. */
  blobUrl: async (path: string): Promise<string> => {
    const token = tokenStore.get();
    const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) throw await parseError(res);
    return URL.createObjectURL(await res.blob());
  },
};
