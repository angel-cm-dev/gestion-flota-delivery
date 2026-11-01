import { ArrowLeft, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { Driver, Order, Page, RouteDetail, RoutePreview, Vehicle } from '../api/types';
import MapView from '../components/MapView';
import { AsyncContent, Button, Card, Field, FormError, Input, PageHeader, Select, useToast } from '../components/ui';
import { formatKg, formatKm, todayLima } from '../lib/format';
import { useAsync } from '../lib/hooks';
import { ORDER_COLORS, VEHICLE_TYPE_LABELS } from '../lib/status';

/** Porcentaje de capacidad usado (se muestra en rojo si se excede). */
export function capacityUsage(weights: number[], capacity: number): { total: number; pct: number; exceeded: boolean } {
  const total = Math.round(weights.reduce((a, b) => a + b, 0) * 100) / 100;
  const pct = capacity > 0 ? Math.round((total / capacity) * 1000) / 10 : 0;
  return { total, pct, exceeded: total > capacity };
}

export default function RoutePlannerPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [date, setDate] = useState(todayLima());
  const [vehicleId, setVehicleId] = useState('');
  const [driverId, setDriverId] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [preview, setPreview] = useState<RoutePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const resources = useAsync(
    () =>
      Promise.all([
        api.get<Page<Vehicle>>('/api/vehicles', { status: 'activo', size: 100 }),
        api.get<Page<Driver>>('/api/drivers', { size: 100 }),
      ]),
    [],
  );
  const orders = useAsync(
    () => api.get<Page<Order>>('/api/orders', { status: 'pendiente', date_from: date, date_to: date, size: 100, sort: 'district' }),
    [date],
  );

  const vehicles = resources.data?.[0].items ?? [];
  const drivers = (resources.data?.[1].items ?? []).filter((d) => d.status !== 'inactivo');
  const vehicle = vehicles.find((v) => String(v.id) === vehicleId);
  const pending = orders.data?.items ?? [];
  const chosen = pending.filter((o) => selected.has(o.id));
  const usage = useMemo(() => capacityUsage(chosen.map((o) => o.weight_kg), vehicle?.capacity_kg ?? 0), [chosen, vehicle]);

  function toggle(id: number) {
    setPreview(null);
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function doPreview() {
    setBusy(true);
    setError(null);
    try {
      setPreview(await api.post<RoutePreview>('/api/routes/preview', { order_ids: [...selected] }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Error inesperado');
    } finally {
      setBusy(false);
    }
  }

  async function create() {
    if (!vehicleId || !driverId) return setError('Selecciona vehículo y conductor');
    setBusy(true);
    setError(null);
    try {
      const route = await api.post<RouteDetail>('/api/routes', { route_date: date, vehicle_id: Number(vehicleId), driver_id: Number(driverId), order_ids: [...selected] });
      toast(`Ruta ${route.code} creada`);
      navigate(`/rutas/${route.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Error inesperado');
    } finally {
      setBusy(false);
    }
  }

  const seqById = new Map(preview?.stops.map((s) => [s.order_id, s.sequence]));
  const path: [number, number][] | undefined = preview
    ? [[preview.depot_lat, preview.depot_lng], ...preview.stops.map((s) => [s.latitude, s.longitude] as [number, number]), [preview.depot_lat, preview.depot_lng]]
    : undefined;

  return (
    <>
      <Link to="/rutas" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
        <ArrowLeft className="h-4 w-4" /> Volver a rutas
      </Link>
      <PageHeader title="Planificar ruta" subtitle="Elige vehículo, conductor y pedidos; el sistema valida capacidad y documentos y optimiza el orden." />
      <AsyncContent loading={resources.loading} error={resources.error} onRetry={resources.reload}>
        <div className="grid gap-6 lg:grid-cols-5">
          <div className="space-y-4 lg:col-span-2">
            <Card className="space-y-4 p-4">
              <FormError message={error} />
              <Field label="Fecha" htmlFor="route-date">
                <Input id="route-date" type="date" min={todayLima()} value={date} onChange={(e) => { setDate(e.target.value); setSelected(new Set()); setPreview(null); }} />
              </Field>
              <Field label="Vehículo" htmlFor="vehicle">
                <Select id="vehicle" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
                  <option value="">Selecciona…</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.plate} · {VEHICLE_TYPE_LABELS[v.vehicle_type]} · {formatKg(v.capacity_kg)}
                      {v.soat.status === 'vencido' || v.tech_review.status === 'vencido' ? ' · documentos vencidos' : ''}
                      {v.maintenance.status === 'vencido' ? ' · mantenimiento vencido' : ''}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Conductor" htmlFor="driver">
                <Select id="driver" value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                  <option value="">Selecciona…</option>
                  {drivers.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.full_name} · {d.license_category}{d.status === 'en_ruta' ? ' · en ruta' : ''}
                    </option>
                  ))}
                </Select>
              </Field>
              <div>
                <div className="mb-1 flex justify-between text-sm">
                  <span>Carga: {formatKg(usage.total)}</span>
                  <span className={usage.exceeded ? 'font-semibold text-red-600' : 'text-slate-500'}>{vehicle ? `${usage.pct}% de ${formatKg(vehicle.capacity_kg)}` : 'sin vehículo'}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                  <div className={`h-2 rounded-full ${usage.exceeded ? 'bg-red-500' : 'bg-brand-500'}`} style={{ width: `${Math.min(usage.pct, 100)}%` }} />
                </div>
                {usage.exceeded && <p className="mt-1 text-xs text-red-600">La carga excede la capacidad del vehículo.</p>}
              </div>
              {preview && (
                <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300">
                  Recorrido optimizado: <strong>{formatKm(preview.total_km)}</strong> (vs {formatKm(preview.unoptimized_km)} en el orden elegido, ahorro {preview.savings_pct}%).
                </div>
              )}
              <div className="flex gap-2">
                <Button variant="secondary" onClick={doPreview} disabled={selected.size === 0} loading={busy && !preview}>
                  <Sparkles className="h-4 w-4" /> Optimizar
                </Button>
                <Button onClick={create} disabled={selected.size === 0 || usage.exceeded} loading={busy}>
                  Crear ruta ({selected.size})
                </Button>
              </div>
            </Card>
            <Card>
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 text-sm dark:border-slate-800">
                <span className="font-semibold">Pedidos pendientes</span>
                {pending.length > 0 && (
                  <button className="text-brand-600 hover:underline dark:text-brand-400" onClick={() => { setPreview(null); setSelected(selected.size === pending.length ? new Set() : new Set(pending.map((o) => o.id))); }}>
                    {selected.size === pending.length ? 'Quitar todos' : 'Seleccionar todos'}
                  </button>
                )}
              </div>
              <AsyncContent loading={orders.loading} error={orders.error} onRetry={orders.reload} empty={pending.length === 0} emptyTitle="Sin pedidos pendientes para esa fecha">
                <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800">
                  {pending.map((o) => (
                    <li key={o.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <input type="checkbox" checked={selected.has(o.id)} onChange={() => toggle(o.id)} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
                        <span className="flex-1">
                          <span className="font-mono text-xs">{o.code}</span> · {o.district}
                          <span className="block text-xs text-slate-500">{o.address}</span>
                        </span>
                        <span className="text-xs text-slate-500">{formatKg(o.weight_kg)}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </AsyncContent>
            </Card>
          </div>
          <Card className="p-4 lg:col-span-3">
            <MapView
              height={620}
              depot={preview ? { lat: preview.depot_lat, lng: preview.depot_lng } : undefined}
              path={path}
              points={pending.map((o) => ({
                id: o.id,
                lat: o.latitude,
                lng: o.longitude,
                color: selected.has(o.id) ? ORDER_COLORS.en_ruta : ORDER_COLORS.pendiente,
                label: o.code,
                sequence: seqById.get(o.id),
              }))}
            />
          </Card>
        </div>
      </AsyncContent>
    </>
  );
}
