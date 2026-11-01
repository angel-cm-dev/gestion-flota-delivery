import { Pencil, Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { Page, Role, User } from '../api/types';
import { AsyncContent, Badge, Button, Card, Field, FormError, Input, Modal, PageHeader, Pagination, SearchInput, Select, Table, Td, useToast } from '../components/ui';
import { formatDateTime } from '../lib/format';
import { useAsync, useDebounced } from '../lib/hooks';
import { ROLE_LABELS } from '../lib/status';
import { isEmail, passwordIssues } from '../lib/validation';

export default function UsersPage() {
  const toast = useToast();
  const [q, setQ] = useState('');
  const [role, setRole] = useState('');
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const [editing, setEditing] = useState<User | 'new' | null>(null);
  const { data, loading, error, reload } = useAsync(() => api.get<Page<User>>('/api/users', { q: dq, role, page, size: 10, sort: 'full_name' }), [dq, role, page]);

  return (
    <>
      <PageHeader title="Usuarios" subtitle="Cuentas y roles de acceso" actions={<Button onClick={() => setEditing('new')}><Plus className="h-4 w-4" /> Nuevo usuario</Button>} />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <SearchInput value={q} onChange={(v) => { setQ(v); setPage(1); }} placeholder="Nombre o email" />
          <Select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }} className="md:w-44" aria-label="Rol">
            <option value="">Todos los roles</option>
            {Object.entries(ROLE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </Select>
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.items.length === 0}>
          <Table head={['Nombre', 'Email', 'Rol', 'Estado', 'Creado', '']}>
            {data?.items.map((u) => (
              <tr key={u.id}>
                <Td className="font-medium">{u.full_name}</Td>
                <Td>{u.email}</Td>
                <Td><Badge tone={u.role === 'admin' ? 'violet' : u.role === 'despachador' ? 'blue' : 'slate'}>{ROLE_LABELS[u.role]}</Badge></Td>
                <Td><Badge tone={u.is_active ? 'green' : 'red'}>{u.is_active ? 'Activo' : 'Desactivado'}</Badge></Td>
                <Td>{formatDateTime(u.created_at)}</Td>
                <Td className="text-right"><Button variant="ghost" className="px-2" onClick={() => setEditing(u)} aria-label={`Editar ${u.email}`}><Pencil className="h-4 w-4" /></Button></Td>
              </tr>
            ))}
          </Table>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
      {editing && <UserForm user={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); toast('Usuario guardado'); reload(); }} />}
    </>
  );
}

function UserForm({ user, onClose, onSaved }: { user: User | null; onClose: () => void; onSaved: () => void }) {
  const [v, setV] = useState({ email: user?.email ?? '', full_name: user?.full_name ?? '', role: (user?.role ?? 'despachador') as Role, is_active: user?.is_active ?? true, password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!user && !isEmail(v.email)) errs.email = 'Email inválido';
    if (v.full_name.trim().length < 3) errs.full_name = 'Requerido';
    const issues = passwordIssues(v.password);
    if ((!user || v.password) && issues.length) errs.password = `Falta: ${issues.join(', ')}`;
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setSaving(true);
    setApiError(null);
    try {
      if (user) await api.put(`/api/users/${user.id}`, { full_name: v.full_name, role: v.role, is_active: v.is_active, password: v.password || null });
      else await api.post('/api/users', { email: v.email, full_name: v.full_name, role: v.role, password: v.password });
      onSaved();
    } catch (err) {
      setApiError(err instanceof ApiError ? err.message : 'Error inesperado');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={user ? `Editar ${user.email}` : 'Nuevo usuario'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <FormError message={apiError} />
        <Field label="Email" htmlFor="u-email" error={errors.email}><Input id="u-email" type="email" value={v.email} disabled={!!user} onChange={(e) => setV({ ...v, email: e.target.value })} /></Field>
        <Field label="Nombre completo" htmlFor="u-name" error={errors.full_name}><Input id="u-name" value={v.full_name} onChange={(e) => setV({ ...v, full_name: e.target.value })} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Rol" htmlFor="u-role">
            <Select id="u-role" value={v.role} onChange={(e) => setV({ ...v, role: e.target.value as Role })}>
              {Object.entries(ROLE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </Select>
          </Field>
          {user && (
            <Field label="Estado" htmlFor="u-active">
              <Select id="u-active" value={v.is_active ? '1' : '0'} onChange={(e) => setV({ ...v, is_active: e.target.value === '1' })}>
                <option value="1">Activo</option>
                <option value="0">Desactivado</option>
              </Select>
            </Field>
          )}
        </div>
        <Field label={user ? 'Nueva contraseña (opcional)' : 'Contraseña'} htmlFor="u-pwd" error={errors.password} hint="Mín. 8 caracteres con mayúscula, minúscula y número">
          <Input id="u-pwd" type="password" autoComplete="new-password" value={v.password} onChange={(e) => setV({ ...v, password: e.target.value })} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit" loading={saving}>Guardar</Button>
        </div>
      </form>
    </Modal>
  );
}
