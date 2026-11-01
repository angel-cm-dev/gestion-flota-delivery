// Etiquetas y colores de estados, en un solo lugar para que toda la UI sea consistente.

export type Tone = 'green' | 'amber' | 'red' | 'blue' | 'slate' | 'violet';

const MAP: Record<string, { label: string; tone: Tone }> = {
  // pedidos
  pendiente: { label: 'Pendiente', tone: 'slate' },
  asignado: { label: 'Asignado', tone: 'violet' },
  en_ruta: { label: 'En ruta', tone: 'blue' },
  entregado: { label: 'Entregado', tone: 'green' },
  fallido: { label: 'Fallido', tone: 'red' },
  cancelado: { label: 'Cancelado', tone: 'slate' },
  // rutas
  planificada: { label: 'Planificada', tone: 'violet' },
  en_curso: { label: 'En curso', tone: 'blue' },
  completada: { label: 'Completada', tone: 'green' },
  cancelada: { label: 'Cancelada', tone: 'slate' },
  // vehículos / conductores
  activo: { label: 'Activo', tone: 'green' },
  mantenimiento: { label: 'En taller', tone: 'amber' },
  inactivo: { label: 'Inactivo', tone: 'slate' },
  disponible: { label: 'Disponible', tone: 'green' },
  // documentos / mantenimiento
  vigente: { label: 'Vigente', tone: 'green' },
  por_vencer: { label: 'Por vencer', tone: 'amber' },
  vencido: { label: 'Vencido', tone: 'red' },
  al_dia: { label: 'Al día', tone: 'green' },
  proximo: { label: 'Próximo', tone: 'amber' },
  // alertas
  critica: { label: 'Crítica', tone: 'red' },
  advertencia: { label: 'Advertencia', tone: 'amber' },
};

export function statusInfo(status: string): { label: string; tone: Tone } {
  return MAP[status] ?? { label: status.replace(/_/g, ' '), tone: 'slate' };
}

/** Color hexadecimal para marcadores del mapa según estado del pedido. */
export const ORDER_COLORS: Record<string, string> = {
  pendiente: '#64748b',
  asignado: '#8b5cf6',
  en_ruta: '#2563eb',
  entregado: '#16a34a',
  fallido: '#dc2626',
  cancelado: '#94a3b8',
};

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  despachador: 'Despachador',
  conductor: 'Conductor',
};

export const VEHICLE_TYPE_LABELS: Record<string, string> = {
  moto: 'Moto',
  auto: 'Auto',
  furgoneta: 'Furgoneta',
  camion: 'Camión',
};
