import { Pencil, Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { Driver, Page } from '../api/types';
import { AsyncContent, Button, Card, Field, FormError, Input, Modal, PageHeader, Pagination, SearchInput, Select, StatusBadge, Table, Td, useToast } from '../components/ui';
import { daysLabel, formatDate } from '../lib/format';
import { useAsync, useDebounced } from '../lib/hooks';
import { isDni, isLicenseNumber, isMobilePe } from '../lib/validation';

const CATEGORIES = ['A-I', 'A-IIa', 'A-IIb', 'A-IIIa', 'A-IIIb', 'A-IIIc', 'B-I', 'B-IIa', 'B-IIb', 'B-IIc'];

type FormValues = {
  full_name: string;
  dni: string;
  phone: string;
  license_number: string;
  license_category: string;
  license_expiry: string;
  status: string;
};

export function validateDriver(v: FormValues): Partial<Record<keyof FormValues, string>> {
  const e: Partial<Record<keyof FormValues, string>> = {};
  if (v.full_name.trim().length < 3) e.full_name = 'Ingresa el nombre completo';
  if (!isDni(v.dni)) e.dni = 'El DNI tiene 8 dígitos';
  if (!isMobilePe(v.phone)) e.phone = 'Celular de 9 dígitos que empieza en 9';
  if (!isLicenseNumber(v.license_number)) e.license_number = 'Letra + 8 dígitos (p. ej. Q45781236)';
  else if (isDni(v.dni) && v.license_number.trim().slice(1) !== v.dni) e.license_number = 'Debe corresponder al DNI';
  if (!v.license_expiry) e.license_expiry = 'Requerido';
  return e;
}

export default function DriversPage() {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const [editing, setEditing] = useState<Driver | 'new' | null>(null);
  const { data, loading, error, reload } = useAsync(
    () => api.get<Page<Driver>>('/api/drivers', { q: dq, status, page, size: 10 }),
    [dq, status, page],
  );

  return (
    <>
      <PageHeader
        title="Conductores"
        subtitle="Licencias de conducir y disponibilidad"
        actions={<Button onClick={() => setEditing('new')}><Plus className="h-4 w-4" /> Nuevo conductor</Button>}
      />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Nombre, DNI o licencia" />
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="md:w-44" aria-label="Estado">
            <option value="">Todos los estados</option>
            <option value="disponible">Disponible</option>
            <option value="en_ruta">En ruta</option>
            <option value="inactivo">Inactivo</option>
          </Select>
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.items.length === 0} emptyTitle="No hay conductores con esos filtros">
          <Table head={['Nombre', 'DNI', 'Celular', 'Licencia', 'Vigencia', 'Estado', '']}>
            {data?.items.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <Td className="font-medium">{d.full_name}</Td>
                <Td>{d.dni}</Td>
                <Td>{d.phone}</Td>
                <Td><span className="font-mono">{d.license_number}</span> <span className="text-slate-500">· {d.license_category}</span></Td>
                <Td><StatusBadge status={d.license.status} /> <span className="text-xs text-slate-500" title={formatDate(d.license.expiry)}>{daysLabel(d.license.days_left)}</span></Td>
                <Td><StatusBadge status={d.status} /></Td>
                <Td className="text-right">
                  <Button variant="ghost" className="px-2" onClick={() => setEditing(d)} aria-label={`Editar ${d.full_name}`}><Pencil className="h-4 w-4" /></Button>
                </Td>
              </tr>
            ))}
          </Table>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {editing && (
        <DriverForm
          driver={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); toast('Conductor guardado'); reload(); }}
        />
      )}
    </>
  );
}

function DriverForm({ driver, onClose, onSaved }: { driver: Driver | null; onClose: () => void; onSaved: () => void }) {
  const [values, setValues] = useState<FormValues>(
    driver
      ? { full_name: driver.full_name, dni: driver.dni, phone: driver.phone, license_number: driver.license_number, license_category: driver.license_category, license_expiry: driver.license.expiry, status: driver.status }
      : { full_name: '', dni: '', phone: '', license_number: '', license_category: 'A-IIa', license_expiry: '', status: 'disponible' },
  );
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof FormValues) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs = validateDriver(values);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const body = { ...values, license_number: values.license_number.trim().toUpperCase(), user_id: driver?.user_id ?? null };
    setSaving(true);
    setApiError(null);
    try {
      if (driver) await api.put(`/api/drivers/${driver.id}`, body);
      else await api.post('/api/drivers', body);
      onSaved();
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : 'Error inesperado');
      if (err instanceof ApiError) setErrors(err.fieldErrors() as typeof errors);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={driver ? `Editar ${driver.full_name}` : 'Nuevo conductor'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <Field label="Nombre completo" htmlFor="full_name" error={errors.full_name}>
          <Input id="full_name" value={values.full_name} onChange={set('full_name')} invalid={!!errors.full_name} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="DNI" htmlFor="dni" error={errors.dni}>
            <Input id="dni" inputMode="numeric" maxLength={8} value={values.dni} onChange={set('dni')} invalid={!!errors.dni} />
          </Field>
          <Field label="Celular" htmlFor="phone" error={errors.phone}>
            <Input id="phone" inputMode="tel" maxLength={9} value={values.phone} onChange={set('phone')} invalid={!!errors.phone} />
          </Field>
          <Field label="N.º de licencia" htmlFor="license_number" error={errors.license_number} hint="Letra + DNI">
            <Input id="license_number" value={values.license_number} onChange={set('license_number')} invalid={!!errors.license_number} />
          </Field>
          <Field label="Categoría" htmlFor="license_category">
            <Select id="license_category" value={values.license_category} onChange={set('license_category')}>
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </Select>
          </Field>
          <Field label="Vencimiento de licencia" htmlFor="license_expiry" error={errors.license_expiry}>
            <Input id="license_expiry" type="date" value={values.license_expiry} onChange={set('license_expiry')} invalid={!!errors.license_expiry} />
          </Field>
          {driver && (
            <Field label="Estado" htmlFor="status">
              <Select id="status" value={values.status} onChange={set('status')}>
                <option value="disponible">Disponible</option>
                <option value="en_ruta">En ruta</option>
                <option value="inactivo">Inactivo</option>
              </Select>
            </Field>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Guardar</Button>
        </div>
      </form>
    </Modal>
  );
}
