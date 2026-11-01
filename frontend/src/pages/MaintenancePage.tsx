import { Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { MaintenanceOverview, MaintenanceRecord, Page, Vehicle } from '../api/types';
import { AsyncContent, Button, Card, Field, FormError, Input, Modal, PageHeader, Pagination, Select, StatusBadge, Table, Td, useToast } from '../components/ui';
import { formatDate, formatKm, formatMoney, todayLima } from '../lib/format';
import { useAsync } from '../lib/hooks';

export default function MaintenancePage() {
  const toast = useToast();
  const [vehicleId, setVehicleId] = useState('');
  const [kind, setKind] = useState('');
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const overview = useAsync(() => api.get<MaintenanceOverview[]>('/api/maintenance/overview'), []);
  const vehicles = useAsync(() => api.get<Page<Vehicle>>('/api/vehicles', { size: 100 }), []);
  const records = useAsync(
    () => api.get<Page<MaintenanceRecord>>('/api/maintenance', { vehicle_id: vehicleId, kind, page, size: 10 }),
    [vehicleId, kind, page],
  );

  return (
    <>
      <PageHeader
        title="Mantenimiento"
        subtitle="Preventivo por kilometraje y registro de servicios correctivos"
        actions={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> Registrar servicio</Button>}
      />
      <Card className="mb-6">
        <h2 className="border-b border-slate-200 px-4 py-3 font-semibold dark:border-slate-800">Próximos mantenimientos preventivos</h2>
        <AsyncContent loading={overview.loading} error={overview.error} onRetry={overview.reload} empty={overview.data?.length === 0}>
          <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-3">
            {overview.data?.map((o) => (
              <div key={o.vehicle_id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold">{o.plate}</span>
                  <StatusBadge status={o.maintenance.status} />
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  Odómetro {formatKm(o.odometer_km)} · próximo a los {formatKm(o.maintenance.next_due_km)}
                </p>
                <p className={`mt-1 text-sm font-medium ${o.maintenance.km_remaining <= 0 ? 'text-red-600' : ''}`}>
                  {o.maintenance.km_remaining <= 0 ? `Vencido por ${formatKm(-o.maintenance.km_remaining)}` : `Faltan ${formatKm(o.maintenance.km_remaining)}`}
                </p>
              </div>
            ))}
          </div>
        </AsyncContent>
      </Card>
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <Select value={vehicleId} onChange={(e) => { setVehicleId(e.target.value); setPage(1); }} className="md:w-52" aria-label="Vehículo">
            <option value="">Todos los vehículos</option>
            {vehicles.data?.items.map((v) => <option key={v.id} value={v.id}>{v.plate}</option>)}
          </Select>
          <Select value={kind} onChange={(e) => { setKind(e.target.value); setPage(1); }} className="md:w-44" aria-label="Tipo">
            <option value="">Todos los tipos</option>
            <option value="preventivo">Preventivo</option>
            <option value="correctivo">Correctivo</option>
          </Select>
        </div>
        <AsyncContent loading={records.loading} error={records.error} onRetry={records.reload} empty={records.data?.items.length === 0} emptyTitle="Sin servicios registrados">
          <Table head={['Fecha', 'Vehículo', 'Tipo', 'Descripción', 'Kilometraje', 'Costo', 'Taller']}>
            {records.data?.items.map((m) => (
              <tr key={m.id}>
                <Td>{formatDate(m.service_date)}</Td>
                <Td className="font-mono">{m.vehicle_plate}</Td>
                <Td className="capitalize">{m.kind}</Td>
                <Td>{m.description}</Td>
                <Td>{formatKm(m.odometer_km)}</Td>
                <Td>{formatMoney(m.cost)}</Td>
                <Td>{m.workshop ?? '—'}</Td>
              </tr>
            ))}
          </Table>
          {records.data && <Pagination page={records.data.page} pages={records.data.pages} total={records.data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {creating && vehicles.data && (
        <MaintenanceForm
          vehicles={vehicles.data.items}
          onClose={() => setCreating(false)}
          onSaved={() => { setCreating(false); toast('Servicio registrado'); records.reload(); overview.reload(); }}
        />
      )}
    </>
  );
}

function MaintenanceForm({ vehicles, onClose, onSaved }: { vehicles: Vehicle[]; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState({ vehicle_id: '', kind: 'preventivo', description: '', odometer_km: '', cost: '', service_date: todayLima(), workshop: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((x) => ({ ...x, [k]: e.target.value }));
  const vehicle = vehicles.find((x) => String(x.id) === v.vehicle_id);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!v.vehicle_id) errs.vehicle_id = 'Selecciona un vehículo';
    if (v.description.trim().length < 3) errs.description = 'Describe el servicio';
    if (!(Number(v.odometer_km) >= 0) || v.odometer_km === '') errs.odometer_km = 'Kilometraje inválido';
    if (!(Number(v.cost) >= 0) || v.cost === '') errs.cost = 'Costo inválido';
    if (v.service_date > todayLima()) errs.service_date = 'No puede ser futura';
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setSaving(true);
    setApiError(null);
    try {
      await api.post('/api/maintenance', { ...v, vehicle_id: Number(v.vehicle_id), odometer_km: Number(v.odometer_km), cost: Number(v.cost), workshop: v.workshop || null });
      onSaved();
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title="Registrar servicio de mantenimiento" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Vehículo" htmlFor="m-vehicle" error={errors.vehicle_id}>
            <Select id="m-vehicle" value={v.vehicle_id} onChange={(e) => { const veh = vehicles.find((x) => String(x.id) === e.target.value); setV((x) => ({ ...x, vehicle_id: e.target.value, odometer_km: veh ? String(veh.odometer_km) : x.odometer_km })); }}>
              <option value="">Selecciona…</option>
              {vehicles.map((x) => <option key={x.id} value={x.id}>{x.plate}</option>)}
            </Select>
          </Field>
          <Field label="Tipo" htmlFor="m-kind" hint={v.kind === 'preventivo' ? 'Reinicia el contador de kilometraje' : undefined}>
            <Select id="m-kind" value={v.kind} onChange={set('kind')}>
              <option value="preventivo">Preventivo</option>
              <option value="correctivo">Correctivo</option>
            </Select>
          </Field>
        </div>
        <Field label="Descripción" htmlFor="m-desc" error={errors.description}><Input id="m-desc" value={v.description} onChange={set('description')} /></Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Kilometraje" htmlFor="m-km" error={errors.odometer_km} hint={vehicle ? `Actual: ${formatKm(vehicle.odometer_km)}` : undefined}><Input id="m-km" type="number" value={v.odometer_km} onChange={set('odometer_km')} /></Field>
          <Field label="Costo (S/)" htmlFor="m-cost" error={errors.cost}><Input id="m-cost" type="number" step="0.01" value={v.cost} onChange={set('cost')} /></Field>
          <Field label="Fecha" htmlFor="m-date" error={errors.service_date}><Input id="m-date" type="date" max={todayLima()} value={v.service_date} onChange={set('service_date')} /></Field>
        </div>
        <Field label="Taller (opcional)" htmlFor="m-ws"><Input id="m-ws" value={v.workshop} onChange={set('workshop')} /></Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Guardar</Button>
        </div>
      </form>
    </Modal>
  );
}
