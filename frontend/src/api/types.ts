// Tipos que reflejan los DTOs del backend (app/application/schemas.py).

export type Role = 'admin' | 'despachador' | 'conductor';
export type VehicleType = 'moto' | 'auto' | 'furgoneta' | 'camion';
export type VehicleStatus = 'activo' | 'mantenimiento' | 'inactivo';
export type FuelType = 'gasolina' | 'diesel' | 'glp' | 'gnv' | 'electrico';
export type DriverStatus = 'disponible' | 'en_ruta' | 'inactivo';
export type OrderStatus = 'pendiente' | 'asignado' | 'en_ruta' | 'entregado' | 'fallido' | 'cancelado';
export type RouteStatus = 'planificada' | 'en_curso' | 'completada' | 'cancelada';
export type DocumentStatus = 'vigente' | 'por_vencer' | 'vencido';
export type MaintenanceStatus = 'al_dia' | 'proximo' | 'vencido';

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  driver_id: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface DocumentInfo {
  expiry: string;
  status: DocumentStatus;
  days_left: number;
}

export interface MaintenanceInfo {
  status: MaintenanceStatus;
  next_due_km: number;
  km_remaining: number;
}

export interface Vehicle {
  id: number;
  plate: string;
  brand: string;
  model: string;
  year: number;
  vehicle_type: VehicleType;
  fuel_type: FuelType;
  capacity_kg: number;
  odometer_km: number;
  maintenance_interval_km: number;
  last_maintenance_km: number;
  status: VehicleStatus;
  soat: DocumentInfo;
  tech_review: DocumentInfo;
  maintenance: MaintenanceInfo;
  created_at: string;
}

export interface Driver {
  id: number;
  full_name: string;
  dni: string;
  phone: string;
  license_number: string;
  license_category: string;
  status: DriverStatus;
  user_id: number | null;
  license: DocumentInfo;
  created_at: string;
}

export interface Order {
  id: number;
  code: string;
  customer_name: string;
  customer_phone: string;
  address: string;
  district: string;
  latitude: number;
  longitude: number;
  weight_kg: number;
  scheduled_date: string;
  notes: string | null;
  status: OrderStatus;
  route_id: number | null;
  stop_sequence: number | null;
  delivered_at: string | null;
  proof_note: string | null;
  has_photo: boolean;
  failure_reason: string | null;
  created_at: string;
}

export interface RouteSummary {
  id: number;
  code: string;
  route_date: string;
  status: RouteStatus;
  vehicle: { id: number; plate: string; vehicle_type: VehicleType; capacity_kg: number };
  driver: { id: number; full_name: string; phone: string };
  depot_lat: number;
  depot_lng: number;
  total_distance_km: number;
  total_weight_kg: number;
  utilization_pct: number;
  stops_total: number;
  stops_done: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RouteDetail extends RouteSummary {
  stops: Order[];
}

export interface RoutePreview {
  depot_lat: number;
  depot_lng: number;
  stops: { sequence: number; order_id: number; code: string; latitude: number; longitude: number; leg_km: number }[];
  total_km: number;
  unoptimized_km: number;
  savings_pct: number;
  total_weight_kg: number;
}

export interface MaintenanceRecord {
  id: number;
  vehicle_id: number;
  vehicle_plate: string;
  kind: 'preventivo' | 'correctivo';
  description: string;
  odometer_km: number;
  cost: number;
  service_date: string;
  workshop: string | null;
  created_at: string;
}

export interface MaintenanceOverview {
  vehicle_id: number;
  plate: string;
  odometer_km: number;
  maintenance: MaintenanceInfo;
}

export interface FuelLog {
  id: number;
  vehicle_id: number;
  vehicle_plate: string;
  driver_id: number | null;
  fill_date: string;
  liters: number;
  total_cost: number;
  odometer_km: number;
  station: string | null;
  created_at: string;
}

export interface FuelEfficiency {
  vehicle_id: number;
  plate: string;
  points: { fill_date: string; odometer_km: number; liters: number; km: number; km_per_liter: number; cost_per_km: number | null }[];
  avg_km_per_liter: number | null;
  total_liters: number;
  total_cost: number;
}

export interface Alert {
  kind: 'soat' | 'revision_tecnica' | 'licencia' | 'mantenimiento';
  severity: 'critica' | 'advertencia';
  entity_type: 'vehicle' | 'driver';
  entity_id: number;
  entity_label: string;
  message: string;
  due_date: string | null;
  days_left: number | null;
  km_remaining: number | null;
}

export interface Dashboard {
  date: string;
  orders_today: Partial<Record<OrderStatus, number>>;
  orders_today_total: number;
  success_rate_30d: number | null;
  delivered_last_7_days: { date: string; delivered: number }[];
  vehicles_by_status: Partial<Record<VehicleStatus, number>>;
  drivers_available: number;
  routes_in_progress: number;
  alerts_critical: number;
  alerts_warning: number;
  fuel_cost_month: number;
  map_orders: { id: number; code: string; customer_name: string; latitude: number; longitude: number; status: OrderStatus }[];
  depot_lat: number;
  depot_lng: number;
}
