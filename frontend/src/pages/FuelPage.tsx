import { Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { FuelEfficiency, FuelLog, Page, Vehicle } from '../api/types';
import { AsyncContent, Button, Card, Field, FormError, Input, KpiCard, Modal, PageHeader, Pagination, Select, Table, Td, useToast } from '../components/ui';
import { formatDate, formatKm, formatMoney, formatNumber, todayLima } from '../lib/format';
import { useAsync } from '../lib/hooks';

export default function FuelPage() {
  const toast = useToast();
  const [vehicleId, setVehicleId] = useState('');
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const vehicles = useAsync(() => api.get<Page<Vehicle>>('/api/vehicles', { size: 100 }), []);
  const logs = useAsync(() => api.get<Page<FuelLog>>('/api/fuel', { vehicle_id: vehicleId, page, size: 10 }), [vehicleId, page]);
  const efficiency = useAsync(
    () => (vehicleId ? api.get<FuelEfficiency>(`/api/fuel/efficiency/${vehicleId}`) : Promise.resolve(null)),
    [vehicleId, logs.data?.total],
  );
  const eff = efficiency.data;

  return (
    <>
      <PageHeader
        title="Combustible"
        subtitle="Cargas de combustible y rendimiento (método tanque lleno a tanque lleno)"
        actions={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> Registrar carga</Button>}
      />
      <div className="mb-4">
        <Select value={vehicleId} onChange={(e) => { setVehicleId(e.target.value); setPage(1); }} className="sm:w-64" aria-label="Vehículo">
          <option value="">Todos los vehículos</option>
          {vehicles.data?.items.map((v) => <option key={v.id} value={v.id}>{v.plate} · {v.brand} {v.model}</option>)}
        </Select>
      </div>
      {eff && (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard label="Rendimiento promedio" value={eff.avg_km_per_liter ? `${formatNumber(eff.avg_km_per_liter)} km/l` : '—'} tone="green" />
          <KpiCard label="Litros totales" value={formatNumber(eff.total_liters)} />
          <KpiCard label="Gasto total" value={formatMoney(eff.total_cost)} tone="amber" />
          <KpiCard label="Última medición" value={eff.points.length ? `${formatNumber(eff.points[eff.points.length - 1].km_per_liter)} km/l` : '—'} hint={eff.points.length ? `${formatKm(eff.points[eff.points.length - 1].km)} recorridos` : 'Se necesitan 2 cargas'} tone="violet" />
        </div>
      )}
      <Card>
        <AsyncContent loading={logs.loading} error={logs.error} onRetry={logs.reload} empty={logs.data?.items.length === 0} emptyTitle="Sin cargas registradas">
          <Table head={['Fecha', 'Vehículo', 'Litros', 'Costo', 'S/ por litro', 'Odómetro', 'Grifo']}>
            {logs.data?.items.map((f) => (
              <tr key={f.id}>
                <Td>{formatDate(f.fill_date)}</Td>
                <Td className="font-mono">{f.vehicle_plate}</Td>
                <Td>{formatNumber(f.liters)}</Td>
                <Td>{formatMoney(f.total_cost)}</Td>
                <Td>{formatMoney(f.total_cost / f.liters)}</Td>
                <Td>{formatKm(f.odometer_km)}</Td>
                <Td>{f.station ?? '—'}</Td>
              </tr>
            ))}
          </Table>
          {logs.data && <Pagination page={logs.data.page} pages={logs.data.pages} total={logs.data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {creating && vehicles.data && (
        <FuelForm vehicles={vehicles.data.items} defaultVehicle={vehicleId} onClose={() => setCreating(false)} onSaved={() => { setCreating(false); toast('Carga registrada'); logs.reload(); }} />
      )}
    </>
  );
}

export function FuelForm({ vehicles, defaultVehicle = '', onClose, onSaved }: { vehicles: { id: number; plate: string; odometer_km?: number }[]; defaultVehicle?: string; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState({ vehicle_id: defaultVehicle, fill_date: todayLima(), liters: '', total_cost: '', odometer_km: '', station: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((x) => ({ ...x, [k]: e.target.value }));
  const vehicle = vehicles.find((x) => String(x.id) === v.vehicle_id);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!v.vehicle_id) errs.vehicle_id = 'Selecciona un vehículo';
    if (!(Number(v.liters) > 0)) errs.liters = 'Debe ser mayor a 0';
    if (v.total_cost === '' || !(Number(v.total_cost) >= 0)) errs.total_cost = 'Costo inválido';
    if (!(Number(v.odometer_km) > 0)) errs.odometer_km = 'Kilometraje inválido';
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setSaving(true);
    setApiError(null);
    try {
      await api.post('/api/fuel', { ...v, vehicle_id: Number(v.vehicle_id), liters: Number(v.liters), total_cost: Number(v.total_cost), odometer_km: Number(v.odometer_km), station: v.station || null });
      onSaved();
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title="Registrar carga de combustible" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Vehículo" htmlFor="f-vehicle" error={errors.vehicle_id}>
            <Select id="f-vehicle" value={v.vehicle_id} onChange={set('vehicle_id')}>
              <option value="">Selecciona…</option>
              {vehicles.map((x) => <option key={x.id} value={x.id}>{x.plate}</option>)}
            </Select>
          </Field>
          <Field label="Fecha" htmlFor="f-date"><Input id="f-date" type="date" max={todayLima()} value={v.fill_date} onChange={set('fill_date')} /></Field>
          <Field label="Litros" htmlFor="f-liters" error={errors.liters}><Input id="f-liters" type="number" step="0.01" value={v.liters} onChange={set('liters')} /></Field>
          <Field label="Costo total (S/)" htmlFor="f-cost" error={errors.total_cost}><Input id="f-cost" type="number" step="0.01" value={v.total_cost} onChange={set('total_cost')} /></Field>
          <Field label="Odómetro (km)" htmlFor="f-odo" error={errors.odometer_km} hint={vehicle?.odometer_km !== undefined ? `Último: ${formatKm(vehicle.odometer_km)}` : 'Tanque lleno al registrar'}>
            <Input id="f-odo" type="number" value={v.odometer_km} onChange={set('odometer_km')} />
          </Field>
          <Field label="Grifo (opcional)" htmlFor="f-station"><Input id="f-station" value={v.station} onChange={set('station')} /></Field>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Guardar</Button>
        </div>
      </form>
    </Modal>
  );
}
