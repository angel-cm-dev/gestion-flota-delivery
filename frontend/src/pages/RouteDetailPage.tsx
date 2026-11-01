import { ArrowLeft, Play, XCircle } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { RouteDetail } from '../api/types';
import MapView from '../components/MapView';
import { AsyncContent, Button, Card, KpiCard, PageHeader, StatusBadge, useToast } from '../components/ui';
import { formatDate, formatKg, formatKm } from '../lib/format';
import { useAsync } from '../lib/hooks';
import { ORDER_COLORS } from '../lib/status';

export default function RouteDetailPage() {
  const { id } = useParams();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const { data: route, loading, error, reload, setData } = useAsync(() => api.get<RouteDetail>(`/api/routes/${id}`), [id]);

  async function action(kind: 'start' | 'cancel') {
    if (kind === 'cancel' && !confirm('¿Cancelar la ruta? Los pedidos volverán a pendientes.')) return;
    setBusy(true);
    try {
      setData(await api.post<RouteDetail>(`/api/routes/${id}/${kind}`));
      toast(kind === 'start' ? 'Ruta iniciada' : 'Ruta cancelada');
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'Error inesperado', 'error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Link to="/rutas" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
        <ArrowLeft className="h-4 w-4" /> Volver a rutas
      </Link>
      <AsyncContent loading={loading} error={error} onRetry={reload}>
        {route && (
          <>
            <PageHeader
              title={`Ruta ${route.code}`}
              subtitle={`${formatDate(route.route_date)} · ${route.vehicle.plate} · ${route.driver.full_name}`}
              actions={
                route.status === 'planificada' && (
                  <>
                    <Button variant="secondary" onClick={() => action('cancel')} disabled={busy}><XCircle className="h-4 w-4" /> Cancelar</Button>
                    <Button onClick={() => action('start')} loading={busy}><Play className="h-4 w-4" /> Iniciar ruta</Button>
                  </>
                )
              }
            />
            <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
              <KpiCard label="Estado" value={<StatusBadge status={route.status} />} />
              <KpiCard label="Avance" value={`${route.stops_done}/${route.stops_total}`} hint="paradas cerradas" tone="green" />
              <KpiCard label="Distancia estimada" value={formatKm(route.total_distance_km)} hint="haversine, ida y vuelta" tone="violet" />
              <KpiCard label="Carga" value={formatKg(route.total_weight_kg)} hint={`${route.utilization_pct}% de capacidad`} tone="amber" />
            </div>
            <div className="grid gap-6 lg:grid-cols-5">
              <Card className="lg:col-span-2">
                <h2 className="border-b border-slate-200 px-4 py-3 font-semibold dark:border-slate-800">Paradas en orden</h2>
                <ol className="divide-y divide-slate-100 dark:divide-slate-800">
                  {route.stops.map((s) => (
                    <li key={s.id} className="flex items-start gap-3 px-4 py-3 text-sm">
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-semibold text-white" style={{ background: ORDER_COLORS[s.status] }}>
                        {s.stop_sequence}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium">{s.customer_name}</p>
                        <p className="text-xs text-slate-500">{s.address}, {s.district} · {formatKg(s.weight_kg)}</p>
                        {s.proof_note && <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-400">{s.proof_note}</p>}
                        {s.failure_reason && <p className="mt-1 text-xs text-red-600">{s.failure_reason}</p>}
                      </div>
                      <StatusBadge status={s.status} />
                    </li>
                  ))}
                </ol>
              </Card>
              <Card className="p-4 lg:col-span-3">
                <MapView
                  height={520}
                  depot={{ lat: route.depot_lat, lng: route.depot_lng }}
                  path={[[route.depot_lat, route.depot_lng], ...route.stops.map((s) => [s.latitude, s.longitude] as [number, number]), [route.depot_lat, route.depot_lng]]}
                  points={route.stops.map((s) => ({ id: s.id, lat: s.latitude, lng: s.longitude, color: ORDER_COLORS[s.status], sequence: s.stop_sequence ?? undefined, popup: <span>{s.code} · {s.customer_name}</span> }))}
                />
              </Card>
            </div>
          </>
        )}
      </AsyncContent>
    </>
  );
}
