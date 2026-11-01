import {
  AlertTriangle,
  Fuel,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  Moon,
  Package,
  Route,
  Sun,
  Truck,
  UserCog,
  Users,
  Wrench,
  X,
} from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import type { Role } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { ROLE_LABELS } from '../lib/status';
import { useTheme } from '../lib/theme';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  roles: Role[];
}

const STAFF: Role[] = ['admin', 'despachador'];
const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" />, roles: STAFF },
  { to: '/pedidos', label: 'Pedidos', icon: <Package className="h-4 w-4" />, roles: STAFF },
  { to: '/rutas', label: 'Rutas', icon: <Route className="h-4 w-4" />, roles: STAFF },
  { to: '/vehiculos', label: 'Vehículos', icon: <Truck className="h-4 w-4" />, roles: STAFF },
  { to: '/conductores', label: 'Conductores', icon: <Users className="h-4 w-4" />, roles: STAFF },
  { to: '/mantenimiento', label: 'Mantenimiento', icon: <Wrench className="h-4 w-4" />, roles: STAFF },
  { to: '/combustible', label: 'Combustible', icon: <Fuel className="h-4 w-4" />, roles: STAFF },
  { to: '/alertas', label: 'Alertas', icon: <AlertTriangle className="h-4 w-4" />, roles: STAFF },
  { to: '/usuarios', label: 'Usuarios', icon: <UserCog className="h-4 w-4" />, roles: ['admin'] },
  { to: '/mis-rutas', label: 'Mis entregas', icon: <Map className="h-4 w-4" />, roles: ['conductor'] },
];

export function Layout() {
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const [open, setOpen] = useState(false);
  if (!user) return null;
  const items = NAV.filter((n) => n.roles.includes(user.role));

  const sidebar = (
    <nav className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white">
          <Truck className="h-5 w-5" />
        </span>
        <div>
          <p className="font-semibold leading-tight">FlotaPe</p>
          <p className="text-xs text-slate-400">Flota y delivery</p>
        </div>
      </div>
      <ul className="flex-1 space-y-0.5 px-3">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="border-t border-slate-800 p-4">
        <p className="truncate text-sm font-medium text-white">{user.full_name}</p>
        <p className="truncate text-xs text-slate-400">
          {ROLE_LABELS[user.role]} · {user.email}
        </p>
        <button onClick={logout} className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
          <LogOut className="h-4 w-4" /> Cerrar sesión
        </button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="fixed inset-y-0 left-0 hidden w-64 bg-slate-900 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-[1001] lg:hidden">
          <div className="absolute inset-0 bg-slate-900/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-slate-900">
            <button className="absolute right-3 top-5 text-slate-400" onClick={() => setOpen(false)} aria-label="Cerrar menú">
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}
      <header className="sticky top-0 z-[999] flex h-14 items-center justify-between border-b border-slate-200 bg-white/80 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80 lg:px-8">
        <button className="rounded-lg p-2 lg:hidden" onClick={() => setOpen(true)} aria-label="Abrir menú">
          <Menu className="h-5 w-5" />
        </button>
        <span className="text-sm text-slate-500 dark:text-slate-400 max-lg:hidden">Lima, Perú · UTC-5</span>
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label={theme === 'dark' ? 'Activar modo claro' : 'Activar modo oscuro'}
          title="Cambiar tema"
        >
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
