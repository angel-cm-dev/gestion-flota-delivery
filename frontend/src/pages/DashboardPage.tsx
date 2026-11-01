import { AlertTriangle, CheckCircle2, Fuel, Package, Route, Truck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Alert, Dashboard } from '../api/types';
import MapView from '../components/MapView';
import { AsyncContent, Card, KpiCard, PageHeader, StatusBadge } from '../components/ui';
import { formatDate, formatMoney } from '../lib/format';
import { useAsync } from '../lib/hooks';
import { ORDER_COLORS, statusInfo } from '../lib/status';

const ORDER_STATES = ['pendiente', 'asignado', 'en_ruta', 'entregado', 'fallido', 'cancelado'] as const;

export default function DashboardPage() {
  const { data, loading, error, reload } = useAsync(
    () => Promise.all([api.get<Dashboard>('/api/dashboard'), api.get<Alert[]>('/api/alerts')]),
    [],
  );
  const [dash, alerts] = data ?? [null, []];

  return (
    <>
      <PageHeader title="Dashboard" subtitle={dash ? `Operación del ${formatDate(dash.date)}` : 'Resumen operativo del día'} />
      <AsyncContent loading={loading} error={error} onRetry={reload}>
        {dash && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <KpiCard label="Pedidos de hoy" value={dash.orders_today_total} hint={`${dash.orders_today.pendiente ?? 0} pendientes de asignar`} icon={<Package className="h-4 w-4" />} />
              <KpiCard
                label="Entregados hoy"
                value={dash.orders_today.entregado ?? 0}
                hint={`Éxito 30 días: ${dash.success_rate_30d ?? '—'}%`}
                icon={<CheckCircle2 className="h-4 w-4" />}
                tone="green"
              />
              <KpiCard
                label="Rutas en curso"
                value={dash.routes_in_progress}
                hint={`${dash.drivers_available} conductores disponibles`}
                icon={<Route className="h-4 w-4" />}
                tone="violet"
              />
              <KpiCard
                label="Alertas"
                value={dash.alerts_critical + dash.alerts_warning}
                hint={`${dash.alerts_critical} críticas · ${dash.alerts_warning} advertencias`}
                icon={<AlertTriangle className="h-4 w-4" />}
                tone={dash.alerts_critical ? 'red' : 'amber'}
              />
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="p-4 lg:col-span-2">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="font-semibold">Pedidos de hoy en el mapa</h2>
                  <div className="hidden flex-wrap gap-3 text-xs sm:flex">
                    {ORDER_STATES.map((s) => (
                      <span key={s} className="flex items-center gap-1">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: ORDER_COLORS[s] }} /> {statusInfo(s).label}
                      </span>
                    ))}
                  </div>
                </div>
                <MapView
                  depot={{ lat: dash.depot_lat, lng: dash.depot_lng }}
                  points={dash.map_orders.map((o) => ({
                    id: o.id,
                    lat: o.latitude,
                    lng: o.longitude,
                    color: ORDER_COLORS[o.status],
                    label: o.code,
                    popup: (
                      <div className="space-y-1">
                        <p className="font-semibold">{o.code}</p>
                        <p>{o.customer_name}</p>
                        <StatusBadge status={o.status} />
                      </div>
                    ),
                  }))}
                />
              </Card>

              <div className="space-y-6">
                <Card className="p-4">
                  <h2 className="mb-4 font-semibold">Entregas últimos 7 días</h2>
                  <DeliveriesChart data={dash.delivered_last_7_days} />
                </Card>
                <Card className="p-4">
                  <h2 className="mb-3 font-semibold">Flota</h2>
                  <dl className="grid grid-cols-3 gap-2 text-center">
                    {(['activo', 'mantenimiento', 'inactivo'] as const).map((s) => (
                      <div key={s} className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/60">
                        <dt className="text-xs text-slate-500 dark:text-slate-400">{statusInfo(s).label}</dt>
                        <dd className="text-xl font-semibold">{dash.vehicles_by_status[s] ?? 0}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="mt-4 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <Fuel className="h-4 w-4" /> Combustible del mes: <strong>{formatMoney(dash.fuel_cost_month)}</strong>
                  </div>
                </Card>
              </div>
            </div>

            <Card>
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
                <h2 className="font-semibold">Alertas prioritarias</h2>
                <Link to="/alertas" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-400">
                  Ver todas
                </Link>
              </div>
              {alerts.length === 0 ? (
                <p className="px-4 py-6 text-sm text-slate-500">Sin alertas: toda la flota está al día.</p>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                  {alerts.slice(0, 5).map((a, i) => (
                    <li key={i} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                      <span className="flex items-center gap-2">
                        <Truck className="h-4 w-4 shrink-0 text-slate-400" /> {a.message}
                      </span>
                      <StatusBadge status={a.severity} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        )}
      </AsyncContent>
    </>
  );
}

function DeliveriesChart({ data }: { data: { date: string; delivered: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.delivered));
  return (
    <div className="flex h-36 items-end gap-2" role="img" aria-label="Gráfico de entregas por día">
      {data.map((d) => (
        <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-xs font-medium">{d.delivered}</span>
          <div className="w-full rounded-t bg-brand-500/80" style={{ height: `${(d.delivered / max) * 100}px` }} title={`${formatDate(d.date)}: ${d.delivered}`} />
          <span className="text-[10px] text-slate-500">{formatDate(d.date).slice(0, 5)}</span>
        </div>
      ))}
    </div>
  );
}
