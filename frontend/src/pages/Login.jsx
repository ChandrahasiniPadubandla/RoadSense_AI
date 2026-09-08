import React, { useState, useEffect } from 'react';
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
      <div className="w-full max-w-sm">
        {/* Brand Header */}
        <div className="mb-6 text-center">
          <div className="inline-flex items-center justify-center gap-2 mb-2">
            <span className="h-2.5 w-2.5 rounded-full bg-signal-blue animate-pulse"></span>
            <span className="text-lg font-bold tracking-tight text-asphalt-100">
              RoadSense AI
            </span>
          </div>
          <p className="text-xs text-asphalt-400">
            Smart Traffic Monitoring &amp; Incident Analytics
          </p>
        </div>

        {/* Login Form Card */}
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6 shadow-xl"
        >
          <div className="mb-5 border-b border-asphalt-800 pb-3">
            <h2 className="text-sm font-semibold text-asphalt-100">Sign In</h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              Enter your credentials to continue
            </p>
          </div>

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="you@traffic.gov"
          />

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="password">
            Password
          </label>
          <div className="relative mt-1 mb-4">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 pr-10 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              className="absolute inset-y-0 right-3 flex items-center text-asphalt-400 hover:text-signal-blue transition-colors"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <Eye size={16} strokeWidth={1.8} /> : <EyeOff size={16} strokeWidth={1.8} />}
            </button>
          </div>

          {error && (
            <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-signal-blue py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in…' : 'Sign In'}
          </button>

          <Link
            to="/forgot-password"
            className="mt-4 block text-center text-xs text-signal-blue hover:underline"
          >
            Forgot password?
          </Link>
        </form>
      </div>
    </div>
  );
}
