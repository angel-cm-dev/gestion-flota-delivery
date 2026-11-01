import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { Page, Vehicle } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { AsyncContent, Button, Card, Field, FormError, Input, Modal, PageHeader, Pagination, SearchInput, Select, StatusBadge, Table, Td, useToast } from '../components/ui';
import { daysLabel, formatDate, formatKg, formatKm } from '../lib/format';
import { useAsync, useDebounced } from '../lib/hooks';
import { VEHICLE_TYPE_LABELS } from '../lib/status';
import { normalizePlate } from '../lib/validation';

type FormValues = {
  plate: string;
  brand: string;
  model: string;
  year: string;
  vehicle_type: string;
  fuel_type: string;
  capacity_kg: string;
  odometer_km: string;
  soat_expiry: string;
  tech_review_expiry: string;
  maintenance_interval_km: string;
  last_maintenance_km: string;
  status: string;
};

const EMPTY: FormValues = {
  plate: '',
  brand: '',
  model: '',
  year: String(new Date().getFullYear()),
  vehicle_type: 'furgoneta',
  fuel_type: 'diesel',
  capacity_kg: '',
  odometer_km: '0',
  soat_expiry: '',
  tech_review_expiry: '',
  maintenance_interval_km: '5000',
  last_maintenance_km: '0',
  status: 'activo',
};

export function validateVehicle(v: FormValues): Partial<Record<keyof FormValues, string>> {
  const e: Partial<Record<keyof FormValues, string>> = {};
  if (!normalizePlate(v.plate)) e.plate = 'Formato ABC-123 (autos) o 1234-AB (motos)';
  if (v.brand.trim().length < 2) e.brand = 'Requerido';
  if (!v.model.trim()) e.model = 'Requerido';
  const year = Number(v.year);
  if (!Number.isInteger(year) || year < 1990 || year > new Date().getFullYear() + 1) e.year = 'Año inválido';
  if (!(Number(v.capacity_kg) > 0)) e.capacity_kg = 'Debe ser mayor a 0';
  if (!(Number(v.odometer_km) >= 0)) e.odometer_km = 'No puede ser negativo';
  if (!v.soat_expiry) e.soat_expiry = 'Requerido';
  if (!v.tech_review_expiry) e.tech_review_expiry = 'Requerido';
  if (!(Number(v.maintenance_interval_km) >= 500)) e.maintenance_interval_km = 'Mínimo 500 km';
  if (Number(v.last_maintenance_km) > Number(v.odometer_km)) e.last_maintenance_km = 'No puede superar el odómetro';
  return e;
}

export default function VehiclesPage() {
  const { hasRole } = useAuth();
  const toast = useToast();
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [sort, setSort] = useState('plate');
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const [editing, setEditing] = useState<Vehicle | 'new' | null>(null);

  const { data, loading, error, reload } = useAsync(
    () => api.get<Page<Vehicle>>('/api/vehicles', { q: dq, status, vehicle_type: type, sort, page, size: 10 }),
    [dq, status, type, sort, page],
  );

  async function remove(v: Vehicle) {
    if (!confirm(`¿Eliminar el vehículo ${v.plate}?`)) return;
    try {
      await api.del(`/api/vehicles/${v.id}`);
      toast('Vehículo eliminado');
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'No se pudo eliminar', 'error');
    }
  }

  return (
    <>
      <PageHeader
        title="Vehículos"
        subtitle="Placas, documentos (SOAT y revisión técnica) y mantenimiento por kilometraje"
        actions={
          <Button onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" /> Nuevo vehículo
          </Button>
        }
      />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Placa, marca o modelo" />
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="md:w-40" aria-label="Estado">
            <option value="">Todos los estados</option>
            <option value="activo">Activo</option>
            <option value="mantenimiento">En taller</option>
            <option value="inactivo">Inactivo</option>
          </Select>
          <Select value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} className="md:w-40" aria-label="Tipo">
            <option value="">Todos los tipos</option>
            {Object.entries(VEHICLE_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </Select>
          <Select value={sort} onChange={(e) => setSort(e.target.value)} className="md:w-52" aria-label="Ordenar">
            <option value="plate">Placa (A-Z)</option>
            <option value="soat_expiry">SOAT más próximo</option>
            <option value="tech_review_expiry">Rev. técnica más próxima</option>
            <option value="-capacity_kg">Mayor capacidad</option>
            <option value="-odometer_km">Mayor kilometraje</option>
          </Select>
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.items.length === 0} emptyTitle="No hay vehículos con esos filtros">
          <Table head={['Placa', 'Vehículo', 'Capacidad', 'Odómetro', 'SOAT', 'Rev. técnica', 'Mantenimiento', 'Estado', '']}>
            {data?.items.map((v) => (
              <tr key={v.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <Td className="font-mono font-semibold">{v.plate}</Td>
                <Td>
                  {v.brand} {v.model} <span className="text-slate-400">· {VEHICLE_TYPE_LABELS[v.vehicle_type]} {v.year}</span>
                </Td>
                <Td>{formatKg(v.capacity_kg)}</Td>
                <Td>{formatKm(v.odometer_km)}</Td>
                <Td>
                  <StatusBadge status={v.soat.status} /> <span className="text-xs text-slate-500" title={formatDate(v.soat.expiry)}>{daysLabel(v.soat.days_left)}</span>
                </Td>
                <Td>
                  <StatusBadge status={v.tech_review.status} /> <span className="text-xs text-slate-500" title={formatDate(v.tech_review.expiry)}>{daysLabel(v.tech_review.days_left)}</span>
                </Td>
                <Td>
                  <StatusBadge status={v.maintenance.status} /> <span className="text-xs text-slate-500">{formatKm(v.maintenance.km_remaining)}</span>
                </Td>
                <Td><StatusBadge status={v.status} /></Td>
                <Td className="text-right">
                  <Button variant="ghost" className="px-2" onClick={() => setEditing(v)} aria-label={`Editar ${v.plate}`}><Pencil className="h-4 w-4" /></Button>
                  {hasRole('admin') && (
                    <Button variant="ghost" className="px-2 text-red-600" onClick={() => remove(v)} aria-label={`Eliminar ${v.plate}`}><Trash2 className="h-4 w-4" /></Button>
                  )}
                </Td>
              </tr>
            ))}
          </Table>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {editing && (
        <VehicleForm
          vehicle={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            toast('Vehículo guardado');
            reload();
          }}
        />
      )}
    </>
  );
}

function VehicleForm({ vehicle, onClose, onSaved }: { vehicle: Vehicle | null; onClose: () => void; onSaved: () => void }) {
  const [values, setValues] = useState<FormValues>(() =>
    vehicle
      ? {
          plate: vehicle.plate,
          brand: vehicle.brand,
          model: vehicle.model,
          year: String(vehicle.year),
          vehicle_type: vehicle.vehicle_type,
          fuel_type: vehicle.fuel_type,
          capacity_kg: String(vehicle.capacity_kg),
          odometer_km: String(vehicle.odometer_km),
          soat_expiry: vehicle.soat.expiry,
          tech_review_expiry: vehicle.tech_review.expiry,
          maintenance_interval_km: String(vehicle.maintenance_interval_km),
          last_maintenance_km: String(vehicle.last_maintenance_km),
          status: vehicle.status,
        }
      : EMPTY,
  );
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof FormValues) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs = validateVehicle(values);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const body = {
      ...values,
      plate: normalizePlate(values.plate),
      year: Number(values.year),
      capacity_kg: Number(values.capacity_kg),
      odometer_km: Number(values.odometer_km),
      maintenance_interval_km: Number(values.maintenance_interval_km),
      last_maintenance_km: Number(values.last_maintenance_km),
    };
    setSaving(true);
    setApiError(null);
    try {
      if (vehicle) await api.put(`/api/vehicles/${vehicle.id}`, body);
      else await api.post('/api/vehicles', body);
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
        setErrors(err.fieldErrors() as typeof errors);
      } else setApiError('Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  const f = (k: keyof FormValues, label: string, props: Record<string, unknown> = {}) => (
    <Field label={label} htmlFor={k} error={errors[k]}>
      <Input id={k} value={values[k]} onChange={set(k)} invalid={!!errors[k]} {...props} />
    </Field>
  );

  return (
    <Modal open title={vehicle ? `Editar ${vehicle.plate}` : 'Nuevo vehículo'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <div className="grid gap-4 sm:grid-cols-3">
          {f('plate', 'Placa', { placeholder: 'ABC-123', onBlur: () => setValues((v) => ({ ...v, plate: normalizePlate(v.plate) ?? v.plate })) })}
          {f('brand', 'Marca')}
          {f('model', 'Modelo')}
          {f('year', 'Año', { type: 'number' })}
          <Field label="Tipo" htmlFor="vehicle_type">
            <Select id="vehicle_type" value={values.vehicle_type} onChange={set('vehicle_type')}>
              {Object.entries(VEHICLE_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </Select>
          </Field>
          <Field label="Combustible" htmlFor="fuel_type">
            <Select id="fuel_type" value={values.fuel_type} onChange={set('fuel_type')}>
              {['gasolina', 'diesel', 'glp', 'gnv', 'electrico'].map((x) => <option key={x} value={x}>{x.toUpperCase()}</option>)}
            </Select>
          </Field>
          {f('capacity_kg', 'Capacidad (kg)', { type: 'number', min: 1 })}
          {f('odometer_km', 'Odómetro (km)', { type: 'number', min: 0 })}
          {vehicle && (
            <Field label="Estado" htmlFor="status">
              <Select id="status" value={values.status} onChange={set('status')}>
                <option value="activo">Activo</option>
                <option value="mantenimiento">En taller</option>
                <option value="inactivo">Inactivo</option>
              </Select>
            </Field>
          )}
          {f('soat_expiry', 'Vencimiento SOAT', { type: 'date' })}
          {f('tech_review_expiry', 'Vencimiento revisión técnica', { type: 'date' })}
          {f('maintenance_interval_km', 'Intervalo mantenimiento (km)', { type: 'number' })}
          {f('last_maintenance_km', 'Último mantenimiento (km)', { type: 'number' })}
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Guardar</Button>
        </div>
      </form>
    </Modal>
  );
}
