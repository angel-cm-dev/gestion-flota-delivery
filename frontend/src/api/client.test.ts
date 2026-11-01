import { api, ApiError, buildUrl, parseError, tokenStore, UNAUTHORIZED_EVENT } from './client';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/problem+json' } });

describe('buildUrl', () => {
  it('omite parámetros vacíos', () => {
    expect(buildUrl('/api/orders', { q: '', status: 'pendiente', page: 1, x: undefined, y: null })).toBe('/api/orders?status=pendiente&page=1');
    expect(buildUrl('/api/orders')).toBe('/api/orders');
  });
});

describe('parseError', () => {
  it('convierte ProblemDetails en ApiError con errores por campo', async () => {
    const err = await parseError(
      json(422, { detail: 'Hay datos inválidos', code: 'validation_error', errors: [{ field: 'plate', message: 'Placa inválida' }] }),
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.code).toBe('validation_error');
    expect(err.fieldErrors()).toEqual({ plate: 'Placa inválida' });
  });

  it('usa un mensaje genérico si la respuesta no es JSON', async () => {
    const err = await parseError(new Response('Bad gateway', { status: 502 }));
    expect(err.message).toBe('Error del servidor. Intenta nuevamente.');
  });
});

describe('api', () => {
  afterEach(() => vi.restoreAllMocks());

  it('envía el token Bearer y parsea JSON', async () => {
    tokenStore.set('abc');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(200, { ok: true }));
    await expect(api.get('/api/vehicles', { page: 2 })).resolves.toEqual({ ok: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/vehicles?page=2');
    expect((init!.headers as Record<string, string>).Authorization).toBe('Bearer abc');
  });

  it('emite el evento de sesión expirada ante un 401 con token', async () => {
    tokenStore.set('vencido');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(401, { detail: 'El token expiró', code: 'token_expired' }));
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    await expect(api.get('/api/auth/me')).rejects.toMatchObject({ status: 401, code: 'token_expired' });
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });

  it('traduce un fallo de red en un ApiError legible', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(api.get('/api/x')).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });
});
