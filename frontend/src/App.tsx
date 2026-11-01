import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { Role } from './api/types';
import { homeFor, useAuth } from './auth/AuthContext';
import { Layout } from './components/Layout';
import { EmptyState, Spinner } from './components/ui';
import LoginPage from './pages/LoginPage';

// Carga diferida: las páginas con mapa (Leaflet) no se descargan hasta que se visitan.
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const OrdersPage = lazy(() => import('./pages/OrdersPage'));
const RoutesPage = lazy(() => import('./pages/RoutesPage'));
const RoutePlannerPage = lazy(() => import('./pages/RoutePlannerPage'));
const RouteDetailPage = lazy(() => import('./pages/RouteDetailPage'));
const VehiclesPage = lazy(() => import('./pages/VehiclesPage'));
const DriversPage = lazy(() => import('./pages/DriversPage'));
const MaintenancePage = lazy(() => import('./pages/MaintenancePage'));
const FuelPage = lazy(() => import('./pages/FuelPage'));
const AlertsPage = lazy(() => import('./pages/AlertsPage'));
const UsersPage = lazy(() => import('./pages/UsersPage'));
const MyRoutesPage = lazy(() => import('./pages/MyRoutesPage'));

function RequireAuth({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner label="Verificando sesión…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}

const STAFF: Role[] = ['admin', 'despachador'];

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<RequireAuth roles={STAFF}><DashboardPage /></RequireAuth>} />
          <Route path="pedidos" element={<RequireAuth roles={STAFF}><OrdersPage /></RequireAuth>} />
          <Route path="rutas" element={<RequireAuth roles={STAFF}><RoutesPage /></RequireAuth>} />
          <Route path="rutas/nueva" element={<RequireAuth roles={STAFF}><RoutePlannerPage /></RequireAuth>} />
          <Route path="rutas/:id" element={<RequireAuth roles={STAFF}><RouteDetailPage /></RequireAuth>} />
          <Route path="vehiculos" element={<RequireAuth roles={STAFF}><VehiclesPage /></RequireAuth>} />
          <Route path="conductores" element={<RequireAuth roles={STAFF}><DriversPage /></RequireAuth>} />
          <Route path="mantenimiento" element={<RequireAuth roles={STAFF}><MaintenancePage /></RequireAuth>} />
          <Route path="combustible" element={<RequireAuth roles={STAFF}><FuelPage /></RequireAuth>} />
          <Route path="alertas" element={<RequireAuth roles={STAFF}><AlertsPage /></RequireAuth>} />
          <Route path="usuarios" element={<RequireAuth roles={['admin']}><UsersPage /></RequireAuth>} />
          <Route path="mis-rutas" element={<RequireAuth roles={['conductor']}><MyRoutesPage /></RequireAuth>} />
          <Route path="*" element={<EmptyState title="Página no encontrada" description="La dirección que buscas no existe." />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
