import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/';

  // If already authenticated, redirect to destination or dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Unable to log in. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="mb-6 text-center">
          <div className="inline-flex items-center justify-center gap-2 mb-2">
            <span className="h-3 w-3 rounded-full bg-signal-blue animate-pulse"></span>
            <span className="text-xl font-bold tracking-tight text-asphalt-100">
              RoadSense AI
            </span>
          </div>
          <p className="text-xs text-asphalt-400">
            Smart Traffic Monitoring &amp; Incident Analytics
          </p>
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
          <div className="relative mt-1 mb-4">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 pr-16 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              className="absolute inset-y-0 right-3 flex items-center text-asphalt-400 hover:text-signal-blue"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <Eye size={18} strokeWidth={1.8} /> : <EyeOff size={18} strokeWidth={1.8} />}
            </button>
          </div>

          {error && (
            <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
          <Link
            to="/forgot-password"
            className="mt-4 block text-center text-xs text-signal-blue hover:underline"
          >
            Forgot password?
          </Link>
        </form>

            <div>
              <label className="block text-xs font-medium text-asphalt-300" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-asphalt-700 bg-asphalt-800/80 px-3.5 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue focus:ring-1 focus:ring-signal-blue"
                placeholder="••••••••"
              />
            </div>

            {
    error && (
      <div className="rounded-md border border-signal-red/30 bg-signal-red/10 p-3 text-xs text-signal-red leading-relaxed">
        {error}
      </div>
    )
  }

  <button
    type="submit"
    disabled={isSubmitting}
    className="mt-2 w-full rounded-md bg-signal-blue py-2.5 text-sm font-semibold text-white shadow transition-all hover:bg-signal-blue/90 disabled:opacity-50"
  >
    {isSubmitting ? 'Verifying credentials…' : 'Sign In to Dashboard'}
  </button>
          </form >
        </div >
      </div >
    </div >
  );
}
