import { Plus } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Page, RouteSummary } from '../api/types';
import { AsyncContent, Button, Card, Input, PageHeader, Pagination, Select, StatusBadge, Table, Td } from '../components/ui';
import { formatDate, formatKg, formatKm } from '../lib/format';
import { useAsync } from '../lib/hooks';

export default function RoutesPage() {
  const navigate = useNavigate();
  const [date, setDate] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(
    () => api.get<Page<RouteSummary>>('/api/routes', { route_date: date, status, page, size: 10 }),
    [date, status, page],
  );

  return (
    <>
      <PageHeader
        title="Rutas"
        subtitle="Rutas de reparto con paradas ordenadas por vecino más cercano"
        actions={<Button onClick={() => navigate('/rutas/nueva')}><Plus className="h-4 w-4" /> Planificar ruta</Button>}
      />
      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800 md:flex-row">
          <Input type="date" value={date} onChange={(e) => { setDate(e.target.value); setPage(1); }} className="md:w-44" aria-label="Fecha" />
          <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="md:w-44" aria-label="Estado">
            <option value="">Todos los estados</option>
            <option value="planificada">Planificada</option>
            <option value="en_curso">En curso</option>
            <option value="completada">Completada</option>
            <option value="cancelada">Cancelada</option>
          </Select>
          {(date || status) && <Button variant="ghost" onClick={() => { setDate(''); setStatus(''); }}>Limpiar filtros</Button>}
        </div>
        <AsyncContent loading={loading} error={error} onRetry={reload} empty={data?.items.length === 0} emptyTitle="No hay rutas">
          <Table head={['Código', 'Fecha', 'Vehículo', 'Conductor', 'Avance', 'Distancia', 'Carga', 'Estado']}>
            {data?.items.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <Td><Link to={`/rutas/${r.id}`} className="font-mono text-xs font-semibold text-brand-600 hover:underline dark:text-brand-400">{r.code}</Link></Td>
                <Td>{formatDate(r.route_date)}</Td>
                <Td className="font-mono">{r.vehicle.plate}</Td>
                <Td>{r.driver.full_name}</Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-slate-200 dark:bg-slate-700">
                      <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${r.stops_total ? (100 * r.stops_done) / r.stops_total : 0}%` }} />
                    </div>
                    <span className="text-xs">{r.stops_done}/{r.stops_total}</span>
                  </div>
                </Td>
                <Td>{formatKm(r.total_distance_km)}</Td>
                <Td>{formatKg(r.total_weight_kg)} <span className="text-xs text-slate-500">({r.utilization_pct}%)</span></Td>
                <Td><StatusBadge status={r.status} /></Td>
              </tr>
            ))}
          </Table>
          {data && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />}
        </AsyncContent>
      </Card>
    </>
  );
}
