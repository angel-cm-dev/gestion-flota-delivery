import { Truck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { homeFor, useAuth } from '../auth/AuthContext';
import { Button, Field, FormError, Input } from '../components/ui';
import { isEmail } from '../lib/validation';

const DEMO = [
  { label: 'Admin', email: 'admin@demo.pe' },
  { label: 'Despachador', email: 'despacho@demo.pe' },
  { label: 'Conductor', email: 'conductor@demo.pe' },
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('admin@demo.pe');
  const [password, setPassword] = useState('Demo123!');
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const errs = {
      email: isEmail(email) ? undefined : 'Ingresa un email válido',
      password: password ? undefined : 'Ingresa tu contraseña',
    };
    setErrors(errs);
    if (errs.email || errs.password) return;
    setLoading(true);
    setError(null);
    try {
      const u = await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && u.role !== 'conductor' ? from : homeFor(u.role), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo iniciar sesión');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-slate-900 lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(51,125,252,0.45),transparent_55%)]" />
        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-2 text-lg font-semibold">
            <Truck className="h-6 w-6" /> FlotaPe
          </div>
          <div>
            <h2 className="text-3xl font-semibold leading-tight">Tu flota, tus rutas y tus entregas en un solo lugar.</h2>
            <p className="mt-4 max-w-md text-slate-300">
              Rutas optimizadas por cercanía, alertas de SOAT y revisión técnica, mantenimiento por kilometraje y pruebas de entrega con foto.
            </p>
          </div>
          <p className="text-sm text-slate-400">Datos de demostración ficticios · Lima, Perú</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={onSubmit} className="w-full max-w-sm space-y-5" noValidate>
          <div>
            <h1 className="text-2xl font-semibold">Iniciar sesión</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Usa una cuenta demo (contraseña Demo123!).</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {DEMO.map((d) => (
              <button
                type="button"
                key={d.email}
                onClick={() => {
                  setEmail(d.email);
                  setPassword('Demo123!');
                }}
                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                  email === d.email ? 'border-brand-600 bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300' : 'border-slate-300 dark:border-slate-700'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <FormError message={error} />
          <Field label="Email" htmlFor="email" error={errors.email}>
            <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} invalid={!!errors.email} />
          </Field>
          <Field label="Contraseña" htmlFor="password" error={errors.password}>
            <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} invalid={!!errors.password} />
          </Field>
          <Button type="submit" className="w-full" loading={loading}>
            Ingresar
          </Button>
        </form>
      </div>
    </div>
  );
}
