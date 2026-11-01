import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../auth/AuthContext';
import { validateDriver } from './DriversPage';
import LoginPage from './LoginPage';
import { validateOrder } from './OrdersPage';
import { capacityUsage } from './RoutePlannerPage';
import { validateVehicle } from './VehiclesPage';

describe('validateVehicle', () => {
  const base = {
    plate: 'abc123', brand: 'Toyota', model: 'Hiace', year: '2021', vehicle_type: 'furgoneta', fuel_type: 'diesel',
    capacity_kg: '1000', odometer_km: '5000', soat_expiry: '2027-01-01', tech_review_expiry: '2027-01-01',
    maintenance_interval_km: '5000', last_maintenance_km: '0', status: 'activo',
  };
  it('acepta un vehículo válido', () => expect(validateVehicle(base)).toEqual({}));
  it('marca placa inválida, capacidad y último mantenimiento mayor al odómetro', () => {
    const e = validateVehicle({ ...base, plate: '12-AB', capacity_kg: '0', last_maintenance_km: '6000' });
    expect(Object.keys(e).sort()).toEqual(['capacity_kg', 'last_maintenance_km', 'plate']);
  });
});

describe('validateDriver', () => {
  it('exige que la licencia corresponda al DNI', () => {
    const e = validateDriver({ full_name: 'Ana Ríos', dni: '45781236', phone: '987654321', license_number: 'Q11111111', license_category: 'A-I', license_expiry: '2028-01-01', status: 'disponible' });
    expect(e.license_number).toBe('Debe corresponder al DNI');
  });
});

describe('validateOrder', () => {
  const base = { customer_name: 'Cliente', customer_phone: '987654321', address: 'Av. Arequipa 123', district: 'Lince', latitude: '-12.08', longitude: '-77.03', weight_kg: '5', scheduled_date: '2026-06-15', notes: '' };
  it('acepta un pedido válido', () => expect(validateOrder(base, '2026-06-15')).toEqual({}));
  it('rechaza fecha pasada y coordenadas fuera de Perú', () => {
    const e = validateOrder({ ...base, latitude: '-77.03', longitude: '-12.08', scheduled_date: '2026-06-01' }, '2026-06-15');
    expect(e.scheduled_date).toBeDefined();
    expect(e.latitude).toMatch(/Perú/);
  });
});

describe('capacityUsage', () => {
  it('calcula porcentaje y detecta exceso', () => {
    expect(capacityUsage([10, 20.5], 100)).toEqual({ total: 30.5, pct: 30.5, exceeded: false });
    expect(capacityUsage([60, 41], 100).exceeded).toBe(true);
  });
});

describe('LoginPage', () => {
  it('valida el formulario antes de llamar a la API', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );
    const email = screen.getByLabelText('Email');
    await userEvent.clear(email);
    await userEvent.type(email, 'no-es-email');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(screen.getByText('Ingresa un email válido')).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('muestra el error del backend si las credenciales fallan', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Email o contraseña incorrectos', code: 'invalid_credentials' }), { status: 401 }),
    );
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByText('Email o contraseña incorrectos')).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
