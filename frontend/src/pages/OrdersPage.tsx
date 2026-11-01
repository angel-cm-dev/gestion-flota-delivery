import { CalendarClock, Eye, Plus, XCircle } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { Order, Page } from '../api/types';
import MapView from '../components/MapView';
import { AsyncContent, Button, Card, Field, FormError, Input, Modal, PageHeader, Pagination, SearchInput, Select, StatusBadge, Table, Td, Textarea, useToast } from '../components/ui';
import { formatDate, formatDateTime, formatKg, todayLima } from '../lib/format';
import { useAsync, useDebounced } from '../lib/hooks';
import { ORDER_COLORS } from '../lib/status';
import { isInPeru, isMobilePe } from '../lib/validation';

type FormValues = {
  customer_name: string;
  customer_phone: string;
  address: string;
  district: string;
  latitude: string;
  longitude: string;
  weight_kg: string;
  scheduled_date: string;
  notes: string;
};

export function validateOrder(v: FormValues, today: string): Partial<Record<keyof FormValues, string>> {
  const e: Partial<Record<keyof FormValues, string>> = {};
  if (v.customer_name.trim().length < 3) e.customer_name = 'Ingresa el nombre del cliente';
  if (!isMobilePe(v.customer_phone)) e.customer_phone = 'Celular de 9 dígitos que empieza en 9';
  if (v.address.trim().length < 5) e.address = 'Dirección demasiado corta';
  if (v.district.trim().length < 2) e.district = 'Requerido';
  const lat = Number(v.latitude);
  const lng = Number(v.longitude);
  if (v.latitude === '' || v.longitude === '' || Number.isNaN(lat) || Number.isNaN(lng)) e.latitude = 'Marca la ubicación en el mapa';
  else if (!isInPeru(lat, lng)) e.latitude = 'La ubicación debe estar en Perú (¿invertiste latitud y longitud?)';
  const w = Number(v.weight_kg);
  if (!(w > 0) || w > 5000) e.weight_kg = 'Entre 0.1 y 5000 kg';
  if (!v.scheduled_date) e.scheduled_date = 'Requerido';
  else if (v.scheduled_date < today) e.scheduled_date = 'No puede ser una fecha pasada';
  return e;
}

export default function OrdersPage() {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [date, setDate] = useState(todayLima());
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<Order | null>(null);
  const [rescheduling, setRescheduling] = useState<Order | null>(null);

  const { data, loading, error, reload } = useAsync(
    () => api.get<Page<Order>>('/api/orders', { q: dq, status, date_from: date, date_to: date, page, size: 10, sort: 'code' }),
    [dq, status, date, page],
  );

  async function cancel(o: Order) {
    if (!confirm(`¿Cancelar el pedido ${o.code}?`)) return;
    try {
      await api.post(`/api/orders/${o.id}/cancel`);
      toast('Pedido cancelado');
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'No se pudo cancelar', 'error');
    }
  }

  return (
    <>
      <PageHeader
        title="Pedidos"
        subtitle="Pedidos de entrega con dirección y coordenadas"
        actions={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> Nuevo pedido</Button>}
      />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Código, cliente o dirección" />
          <Input type="date" value={date} onChange={(e) => { setDate(e.target.value); setPage(1); }} className="md:w-44" aria-label="Fecha programada" />
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="md:w-44" aria-label="Estado">
            <option value="">Todos los estados</option>
            {['pendiente', 'asignado', 'en_ruta', 'entregado', 'fallido', 'cancelado'].map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </Select>
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.items.length === 0} emptyTitle="No hay pedidos" emptyDescription="Cambia la fecha o los filtros, o registra un nuevo pedido.">
          <Table head={['Código', 'Cliente', 'Dirección', 'Peso', 'Fecha', 'Estado', '']}>
            {data?.items.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <Td className="font-mono text-xs font-semibold">{o.code}</Td>
                <Td>{o.customer_name}<div className="text-xs text-slate-500">{o.customer_phone}</div></Td>
                <Td>{o.address}<div className="text-xs text-slate-500">{o.district}</div></Td>
                <Td>{formatKg(o.weight_kg)}</Td>
                <Td>{formatDate(o.scheduled_date)}</Td>
                <Td><StatusBadge status={o.status} />{o.stop_sequence && <span className="ml-1 text-xs text-slate-500">parada {o.stop_sequence}</span>}</Td>
                <Td className="text-right">
                  <Button variant="ghost" className="px-2" onClick={() => setViewing(o)} aria-label={`Ver ${o.code}`}><Eye className="h-4 w-4" /></Button>
                  {o.status === 'fallido' && (
                    <Button variant="ghost" className="px-2" onClick={() => setRescheduling(o)} aria-label={`Reprogramar ${o.code}`}><CalendarClock className="h-4 w-4" /></Button>
                  )}
                  {(o.status === 'pendiente' || o.status === 'asignado') && (
                    <Button variant="ghost" className="px-2 text-red-600" onClick={() => cancel(o)} aria-label={`Cancelar ${o.code}`}><XCircle className="h-4 w-4" /></Button>
                  )}
                </Td>
              </tr>
            ))}
          </Table>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {creating && <OrderForm onClose={() => setCreating(false)} onSaved={() => { setCreating(false); toast('Pedido registrado'); reload(); }} />}
      {viewing && <OrderDetail order={viewing} onClose={() => setViewing(null)} />}
      {rescheduling && (
        <RescheduleForm order={rescheduling} onClose={() => setRescheduling(null)} onSaved={() => { setRescheduling(null); toast('Pedido reprogramado'); reload(); }} />
      )}
    </>
  );
}

function OrderForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const today = todayLima();
  const [values, setValues] = useState<FormValues>({ customer_name: '', customer_phone: '', address: '', district: '', latitude: '', longitude: '', weight_kg: '', scheduled_date: today, notes: '' });
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof FormValues) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs = validateOrder(values, today);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setSaving(true);
    setApiError(null);
    try {
      await api.post('/api/orders', { ...values, latitude: Number(values.latitude), longitude: Number(values.longitude), weight_kg: Number(values.weight_kg), notes: values.notes || null });
      onSaved();
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  const hasPoint = values.latitude !== '' && values.longitude !== '';
  return (
    <Modal open title="Nuevo pedido" onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Cliente" htmlFor="customer_name" error={errors.customer_name}><Input id="customer_name" value={values.customer_name} onChange={set('customer_name')} invalid={!!errors.customer_name} /></Field>
          <Field label="Celular" htmlFor="customer_phone" error={errors.customer_phone}><Input id="customer_phone" maxLength={9} value={values.customer_phone} onChange={set('customer_phone')} invalid={!!errors.customer_phone} /></Field>
          <Field label="Dirección" htmlFor="address" error={errors.address}><Input id="address" value={values.address} onChange={set('address')} invalid={!!errors.address} /></Field>
          <Field label="Distrito" htmlFor="district" error={errors.district}><Input id="district" value={values.district} onChange={set('district')} invalid={!!errors.district} /></Field>
          <Field label="Peso (kg)" htmlFor="weight_kg" error={errors.weight_kg}><Input id="weight_kg" type="number" step="0.1" value={values.weight_kg} onChange={set('weight_kg')} invalid={!!errors.weight_kg} /></Field>
          <Field label="Fecha de entrega" htmlFor="scheduled_date" error={errors.scheduled_date}><Input id="scheduled_date" type="date" min={today} value={values.scheduled_date} onChange={set('scheduled_date')} invalid={!!errors.scheduled_date} /></Field>
        </div>
        <Field label="Ubicación (haz clic en el mapa)" error={errors.latitude} hint={hasPoint ? `${values.latitude}, ${values.longitude}` : 'Sin ubicación seleccionada'}>
          <MapView
            height={260}
            points={hasPoint ? [{ id: 'new', lat: Number(values.latitude), lng: Number(values.longitude), color: ORDER_COLORS.pendiente }] : []}
            onPick={(lat, lng) => setValues((v) => ({ ...v, latitude: String(lat), longitude: String(lng) }))}
          />
        </Field>
        <Field label="Notas (opcional)" htmlFor="notes"><Textarea id="notes" value={values.notes} onChange={set('notes')} maxLength={500} /></Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Registrar</Button>
        </div>
      </form>
    </Modal>
  );
}

function OrderDetail({ order, onClose }: { order: Order; onClose: () => void }) {
  const [photo, setPhoto] = useState<string | null>(null);
  useEffect(() => {
    if (!order.has_photo) return;
    let url: string | null = null;
    api.blobUrl(`/api/orders/${order.id}/photo`).then((u) => { url = u; setPhoto(u); }).catch(() => setPhoto(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [order]);
  return (
    <Modal open title={`Pedido ${order.code}`} onClose={onClose}>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-slate-500">Cliente</dt><dd>{order.customer_name}</dd></div>
        <div><dt className="text-slate-500">Estado</dt><dd><StatusBadge status={order.status} /></dd></div>
        <div className="col-span-2"><dt className="text-slate-500">Dirección</dt><dd>{order.address}, {order.district}</dd></div>
        <div><dt className="text-slate-500">Entregado</dt><dd>{formatDateTime(order.delivered_at)}</dd></div>
        <div><dt className="text-slate-500">Peso</dt><dd>{formatKg(order.weight_kg)}</dd></div>
        {order.proof_note && <div className="col-span-2"><dt className="text-slate-500">Nota de entrega</dt><dd>{order.proof_note}</dd></div>}
        {order.failure_reason && <div className="col-span-2"><dt className="text-slate-500">Motivo de falla</dt><dd className="text-red-600">{order.failure_reason}</dd></div>}
      </dl>
      {photo && <img src={photo} alt="Foto de prueba de entrega" className="mt-4 max-h-80 w-full rounded-lg object-contain" />}
      <div className="mt-4">
        <MapView height={200} points={[{ id: order.id, lat: order.latitude, lng: order.longitude, color: ORDER_COLORS[order.status] }]} />
      </div>
    </Modal>
  );
}

function RescheduleForm({ order, onClose, onSaved }: { order: Order; onClose: () => void; onSaved: () => void }) {
  const [date, setDate] = useState(todayLima());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post(`/api/orders/${order.id}/reschedule`, { scheduled_date: date });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal open title={`Reprogramar ${order.code}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-500">Motivo de la falla: {order.failure_reason}</p>
        <FormError message={error} />
        <Field label="Nueva fecha" htmlFor="new-date"><Input id="new-date" type="date" min={todayLima()} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Reprogramar</Button>
        </div>
      </form>
    </Modal>
  );
}
