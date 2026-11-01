import { Camera, CheckCircle2, Fuel, Navigation, Phone, XCircle } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { Order, RouteDetail } from '../api/types';
import MapView from '../components/MapView';
import { AsyncContent, Button, Card, Field, FormError, Input, Modal, PageHeader, StatusBadge, Textarea, useToast } from '../components/ui';
import { formatDate, formatKg, formatKm, todayLima } from '../lib/format';
import { useAsync } from '../lib/hooks';
import { ORDER_COLORS } from '../lib/status';
import { FuelForm } from './FuelPage';

const MAX_PHOTO_MB = 5;

export default function MyRoutesPage() {
  const toast = useToast();
  const [date, setDate] = useState(todayLima());
  const { data, loading, error, reload } = useAsync(() => api.get<RouteDetail[]>('/api/routes/mine', { route_date: date }), [date]);
  const [delivering, setDelivering] = useState<Order | null>(null);
  const [failing, setFailing] = useState<Order | null>(null);
  const [fuelFor, setFuelFor] = useState<RouteDetail | null>(null);

  return (
    <>
      <PageHeader
        title="Mis entregas"
        subtitle="Sigue el orden sugerido y registra la prueba de cada entrega"
        actions={<Input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="Fecha" className="w-44" />}
      />
      <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.length === 0} emptyTitle="No tienes rutas para esta fecha" emptyDescription="Cuando el despachador te asigne una ruta aparecerá aquí.">
        <div className="space-y-6">
          {data?.map((route) => {
            const next = route.stops.find((s) => s.status === 'en_ruta');
            return (
              <Card key={route.id} className="overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4 dark:border-slate-800">
                  <div>
                    <p className="font-semibold">
                      Ruta {route.code} <StatusBadge status={route.status} />
                    </p>
                    <p className="text-sm text-slate-500">
                      {formatDate(route.route_date)} · {route.vehicle.plate} · {route.stops_done}/{route.stops_total} paradas · {formatKm(route.total_distance_km)}
                    </p>
                  </div>
                  {route.status !== 'cancelada' && (
                    <Button variant="secondary" onClick={() => setFuelFor(route)}>
                      <Fuel className="h-4 w-4" /> Registrar combustible
                    </Button>
                  )}
                </div>
                {route.status === 'planificada' && (
                  <p className="bg-violet-50 px-4 py-2 text-sm text-violet-800 dark:bg-violet-500/10 dark:text-violet-300">La ruta aún no fue iniciada por el despachador.</p>
                )}
                <div className="grid gap-0 lg:grid-cols-2">
                  <ol className="divide-y divide-slate-100 dark:divide-slate-800">
                    {route.stops.map((s) => (
                      <li key={s.id} className={`p-4 ${next?.id === s.id ? 'bg-brand-50/60 dark:bg-brand-500/10' : ''}`}>
                        <div className="flex items-start gap-3">
                          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold text-white" style={{ background: ORDER_COLORS[s.status] }}>
                            {s.stop_sequence}
                          </span>
                          <div className="flex-1 text-sm">
                            <p className="font-medium">{s.customer_name}</p>
                            <p className="text-slate-500">{s.address}, {s.district}</p>
                            <p className="text-xs text-slate-500">{formatKg(s.weight_kg)}{s.notes ? ` · ${s.notes}` : ''}</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <a href={`tel:${s.customer_phone}`} className="inline-flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400"><Phone className="h-3 w-3" /> {s.customer_phone}</a>
                              <a href={`https://www.openstreetmap.org/directions?to=${s.latitude},${s.longitude}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400">
                                <Navigation className="h-3 w-3" /> Cómo llegar
                              </a>
                            </div>
                          </div>
                          <StatusBadge status={s.status} />
                        </div>
                        {s.status === 'en_ruta' && (
                          <div className="mt-3 flex gap-2 pl-10">
                            <Button onClick={() => setDelivering(s)} className="flex-1 sm:flex-none"><CheckCircle2 className="h-4 w-4" /> Entregado</Button>
                            <Button variant="secondary" onClick={() => setFailing(s)} className="flex-1 sm:flex-none"><XCircle className="h-4 w-4" /> No entregado</Button>
                          </div>
                        )}
                      </li>
                    ))}
                  </ol>
                  <div className="p-4">
                    <MapView
                      height={420}
                      depot={{ lat: route.depot_lat, lng: route.depot_lng }}
                      path={[[route.depot_lat, route.depot_lng], ...route.stops.map((s) => [s.latitude, s.longitude] as [number, number])]}
                      points={route.stops.map((s) => ({ id: s.id, lat: s.latitude, lng: s.longitude, color: ORDER_COLORS[s.status], sequence: s.stop_sequence ?? undefined }))}
                    />
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </AsyncContent>
      {delivering && <DeliverForm order={delivering} onClose={() => setDelivering(null)} onDone={() => { setDelivering(null); toast('Entrega registrada'); reload(); }} />}
      {failing && <FailForm order={failing} onClose={() => setFailing(null)} onDone={() => { setFailing(null); toast('Entrega marcada como fallida'); reload(); }} />}
      {fuelFor && (
        <FuelForm vehicles={[{ id: fuelFor.vehicle.id, plate: fuelFor.vehicle.plate }]} defaultVehicle={String(fuelFor.vehicle.id)} onClose={() => setFuelFor(null)} onSaved={() => { setFuelFor(null); toast('Carga registrada'); }} />
      )}
    </>
  );
}

function DeliverForm({ order, onClose, onDone }: { order: Order; onClose: () => void; onDone: () => void }) {
  const [note, setNote] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    // Misma regla que el backend: sin evidencia no hay entrega.
    if (!photo && !note.trim()) return setError('Adjunta una foto o escribe quién recibió el pedido.');
    if (photo && photo.size > MAX_PHOTO_MB * 1024 * 1024) return setError(`La foto supera ${MAX_PHOTO_MB} MB.`);
    const form = new FormData();
    if (note.trim()) form.append('note', note.trim());
    if (photo) form.append('photo', photo);
    setSaving(true);
    setError(null);
    try {
      await api.postForm(`/api/orders/${order.id}/deliver`, form);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={`Entregar ${order.code}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <FormError message={error} />
        <Field label="Foto de la entrega" htmlFor="photo" hint="JPG, PNG o WEBP, máx. 5 MB">
          <label htmlFor="photo" className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-4 text-sm text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
            <Camera className="h-5 w-5" /> {photo ? photo.name : 'Tomar o elegir foto'}
          </label>
          <input id="photo" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="sr-only" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
        </Field>
        <Field label="Nota" htmlFor="note" hint="Ej.: Recibió Ana Torres (DNI verificado)">
          <Textarea id="note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Confirmar entrega</Button>
        </div>
      </form>
    </Modal>
  );
}

const REASONS = ['Cliente ausente', 'Dirección incorrecta', 'Rechazado por el cliente', 'Zona inaccesible'];

function FailForm({ order, onClose, onDone }: { order: Order; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState(REASONS[0]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (reason.trim().length < 3) return setError('Indica el motivo');
    setSaving(true);
    try {
      await api.post(`/api/orders/${order.id}/fail`, { reason });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal open title={`No entregado: ${order.code}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <FormError message={error} />
        <div className="flex flex-wrap gap-2">
          {REASONS.map((r) => (
            <button type="button" key={r} onClick={() => setReason(r)} className={`rounded-full border px-3 py-1 text-xs ${reason === r ? 'border-red-500 bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300' : 'border-slate-300 dark:border-slate-700'}`}>
              {r}
            </button>
          ))}
        </div>
        <Field label="Motivo" htmlFor="reason"><Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} /></Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" variant="danger" loading={saving}>Marcar como fallido</Button>
        </div>
      </form>
    </Modal>
  );
}
