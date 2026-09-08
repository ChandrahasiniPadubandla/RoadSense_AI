import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DEMO_ACCOUNTS = [
  { label: 'Super Admin', email: 'admin@traffic.gov', password: 'admin123' },
  { label: 'Traffic Authority', email: 'authority@traffic.gov', password: 'authority123' },
  { label: 'Emergency Response', email: 'response@traffic.gov', password: 'response123' },
  { label: 'Viewer', email: 'viewer@traffic.gov', password: 'viewer123' },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/';

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Unable to log in.');
    } finally {
      setIsSubmitting(false);
    }
  }

  function fillDemo(account) {
    setEmail(account.email);
    setPassword(account.password);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="text-sm font-semibold tracking-tight text-asphalt-100">
            Smart Traffic &amp; Accident Prediction
          </p>
          <p className="mt-1 text-xs text-asphalt-400">Sign in to continue</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6"
        >
          <label className="block text-xs text-asphalt-400" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
            placeholder="you@traffic.gov"
          />

          <label className="block text-xs text-asphalt-400" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
            placeholder="••••••••"
          />

          {error && (
            <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="mt-5 rounded-lg border border-asphalt-800 bg-asphalt-900/50 p-4">
          <p className="mb-2 text-xs text-asphalt-400">
            Demo accounts (mock mode only):
          </p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => fillDemo(acc)}
                className="rounded-md border border-asphalt-700 px-2 py-1.5 text-left text-xs text-asphalt-300 hover:border-signal-blue/50 hover:text-signal-blue"
              >
                {acc.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
