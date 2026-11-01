import { useState } from 'react';
import { api } from '../api/client';
import type { Alert } from '../api/types';
import { AsyncContent, Card, PageHeader, Select, StatusBadge, Table, Td } from '../components/ui';
import { formatDate, formatKm } from '../lib/format';
import { useAsync } from '../lib/hooks';

const KIND_LABELS: Record<Alert['kind'], string> = {
  soat: 'SOAT',
  revision_tecnica: 'Revisión técnica',
  licencia: 'Licencia',
  mantenimiento: 'Mantenimiento',
};

export default function AlertsPage() {
  const [kind, setKind] = useState('');
  const [severity, setSeverity] = useState('');
  const { data, loading, error, reload } = useAsync(() => api.get<Alert[]>('/api/alerts'), []);
  const items = (data ?? []).filter((a) => (!kind || a.kind === kind) && (!severity || a.severity === severity));

  return (
    <>
      <PageHeader title="Alertas" subtitle="Documentos por vencer o vencidos y mantenimientos pendientes (se calculan en tiempo real)" />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 sm:flex-row">
          <Select value={kind} onChange={(e) => setKind(e.target.value)} className="sm:w-52" aria-label="Tipo de alerta">
            <option value="">Todos los tipos</option>
            {Object.entries(KIND_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </Select>
          <Select value={severity} onChange={(e) => setSeverity(e.target.value)} className="sm:w-44" aria-label="Severidad">
            <option value="">Toda severidad</option>
            <option value="critica">Crítica</option>
            <option value="advertencia">Advertencia</option>
          </Select>
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={items.length === 0} emptyTitle="Sin alertas" emptyDescription="Toda la flota tiene documentos y mantenimientos al día.">
          <Table head={['Severidad', 'Tipo', 'Unidad / persona', 'Detalle', 'Vence']}>
            {items.map((a, i) => (
              <tr key={i}>
                <Td><StatusBadge status={a.severity} /></Td>
                <Td>{KIND_LABELS[a.kind]}</Td>
                <Td className="font-medium">{a.entity_label}</Td>
                <Td className="whitespace-normal">{a.message}</Td>
                <Td>{a.due_date ? formatDate(a.due_date) : a.km_remaining !== null ? formatKm(a.km_remaining) : '—'}</Td>
              </tr>
            ))}
          </Table>
        </AsyncContent>
      </Card>
    </>
  );
}
