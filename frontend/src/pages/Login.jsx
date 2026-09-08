import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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

        {/* Login Card */}
        <div className="rounded-xl border border-asphalt-700 bg-asphalt-900/90 p-7 shadow-2xl backdrop-blur">
          <div className="mb-5 border-b border-asphalt-800 pb-3">
            <h2 className="text-base font-semibold text-asphalt-100">System Sign In</h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              Enter your credentials to access the traffic console
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-asphalt-700 bg-asphalt-800/80 px-3.5 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue focus:ring-1 focus:ring-signal-blue"
                placeholder="you@domain.com"
              />
            </div>

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

            {error && (
              <div className="rounded-md border border-signal-red/30 bg-signal-red/10 p-3 text-xs text-signal-red leading-relaxed">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md bg-signal-blue py-2.5 text-sm font-semibold text-white shadow transition-all hover:bg-signal-blue/90 disabled:opacity-50"
            >
              {isSubmitting ? 'Verifying credentials…' : 'Sign In to Dashboard'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
