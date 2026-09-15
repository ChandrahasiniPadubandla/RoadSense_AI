import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { motion } from "framer-motion";

export default function Login() {
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [successMessage] = useState(
    location.state?.registered
      ? 'Account created successfully. Please sign in.'
      : location.state?.verified
        ? 'Email verified successfully. You can now sign in.'
        : ''
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const from = location.state?.from?.pathname || '/';

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
    <motion.div
      className="relative flex min-h-screen items-center justify-center overflow-hidden bg-cover bg-center bg-no-repeat px-4"
      style={{
        backgroundImage:
          "url('https://thumbs.dreamstime.com/b/traffic-jam-night-long-trail-red-brake-lights-seen-mumbai-india-95449126.jpg')",
        backgroundPosition: 'center center'
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
    >
      <div className="absolute inset-0 bg-slate-950/45 backdrop-blur-[1px]" />

      <motion.div
        className="relative z-10 w-full max-w-sm"
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8 }}
        whileHover={{ scale: 1.02 }}
      >
        <motion.div
          className="mb-6 text-center"
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-xl font-bold tracking-tight text-white drop-shadow-lg">
            Smart Traffic Monitoring &amp; Incident Analytics
          </h1>
        </motion.div>

        <motion.form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-white/20 bg-white/10 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.6)] backdrop-blur-xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          whileHover={{ boxShadow: "0 0 30px rgba(96, 165, 250, 0.35)" }}
        >
          <div className="mb-5 border-b border-white/15 pb-3">
            <h2 className="text-sm font-semibold text-white">Sign In</h2>
            <p className="mt-0.5 text-xs text-slate-200/80">
              Enter your credentials to continue
            </p>
          </div>

          <label className="block text-xs font-medium text-slate-100" htmlFor="email">
            Email Address
          </label>
          <motion.input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 mb-4 w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder-slate-300 outline-none transition-colors focus:border-sky-300"
            placeholder="you@traffic.gov"
            whileFocus={{ scale: 1.02, borderColor: '#7dd3fc' }}
          />

          <label className="block text-xs font-medium text-slate-100" htmlFor="password">
            Password
          </label>
          <div className="relative mt-1 mb-4">
            <motion.input
              id="password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-white/20 bg-white/10 px-3 py-2 pr-10 text-sm text-white placeholder-slate-300 outline-none transition-colors focus:border-sky-300"
              placeholder="••••••••"
              whileFocus={{ scale: 1.02, borderColor: '#7dd3fc' }}
            />
            <motion.button
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              className="absolute inset-y-0 right-3 flex items-center text-slate-200 transition-colors hover:text-white"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              title={showPassword ? 'Hide password' : 'Show password'}
              whileTap={{ rotate: 180 }}
            >
              {showPassword ? <Eye size={16} strokeWidth={1.8} /> : <EyeOff size={16} strokeWidth={1.8} />}
            </motion.button>
          </div>

          {successMessage && (
            <motion.p
              className="mb-4 rounded-md border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100"
              initial={{ x: -30, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.6 }}
            >
              {successMessage}
            </motion.p>
          )}

          {error && (
            <motion.p
              className="mb-4 rounded-md border border-rose-300/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-100"
              initial={{ x: 30, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.6 }}
            >
              {error}
            </motion.p>
          )}

          <motion.button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-sky-500/90 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            animate={isSubmitting ? { opacity: [1, 0.6, 1] } : {}}
            transition={{ repeat: isSubmitting ? Infinity : 0, duration: 1 }}
          >
            {isSubmitting ? 'Signing in…' : 'Sign In'}
          </motion.button>

          <div className="mt-4 flex flex-col items-center gap-2 text-xs">
            <Link
              to="/forgot-password"
              className="text-sky-200 hover:text-white hover:underline"
            >
              Forgot password?
            </Link>
            <p className="text-slate-200/90">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="text-sky-200 hover:text-white hover:underline">
                Create one
              </Link>
            </p>
          </div>
        </motion.form>
      </motion.div>
    </motion.div>
  );
}
