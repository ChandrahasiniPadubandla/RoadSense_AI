import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PHONE_REGEX = /^(\+91[\-\s]?|0)?[6-9]\d{9}$|^[0-9]{10}$/;

export default function Register() {
  const { register, verifiedEmail, clearEmailVerification } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const email = verifiedEmail || location.state?.email || '';

  const [form, setForm] = useState({
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function handleUseDifferentEmail() {
    clearEmailVerification();
    navigate('/verify-email');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!email) {
      setError('Missing verified email. Please verify your email first.');
      return;
    }

    if (!form.name.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    let validatedPhone = null;
    const trimmedPhone = form.phone.trim();
    if (trimmedPhone) {
      const cleanedPhone = trimmedPhone.replace(/[\s\-()]/g, '');
      if (!PHONE_REGEX.test(cleanedPhone)) {
        setError('Please enter a valid 10-digit phone number (e.g. 9876543210).');
        return;
      }
      validatedPhone = cleanedPhone;
    }

    setIsSubmitting(true);
    try {
      await register({
        name: form.name.trim(),
        email,
        phone: validatedPhone,
        password: form.password,
      });
      navigate('/login', { state: { registered: true } });
    } catch (err) {
      setError(err.message || 'Unable to create your account. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-bold tracking-tight text-asphalt-100">
            Smart Traffic Monitoring &amp; Incident Analytics
          </h1>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6 shadow-xl"
        >
          <div className="mb-5 border-b border-asphalt-800 pb-3">
            <h2 className="text-sm font-semibold text-asphalt-100">Create your account</h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              Your email <span className="text-asphalt-200">{email}</span> is verified. Finish setting up your account below.
            </p>
          </div>

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            disabled
            value={email}
            className="mt-1 mb-4 w-full cursor-not-allowed rounded-md border border-asphalt-700 bg-asphalt-800/60 px-3 py-2 text-sm text-asphalt-400"
          />

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="name">
            Full Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            required
            autoFocus
            value={form.name}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="Enter your full name"
          />

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="phone">
            Phone Number <span className="text-asphalt-500 font-normal">(Optional)</span>
          </label>
          <input
            id="phone"
            name="phone"
            type="tel"
            value={form.phone}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="10-digit mobile number (e.g. 9876543210)"
          />

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="password">
            Password
          </label>
          <div className="relative mt-1 mb-4">
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              required
              minLength={6}
              value={form.password}
              onChange={handleChange}
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 pr-10 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
              placeholder="At least 6 characters"
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

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="confirmPassword">
            Confirm Password
          </label>
          <div className="relative mt-1 mb-4">
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              required
              minLength={6}
              value={form.confirmPassword}
              onChange={handleChange}
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 pr-10 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
              placeholder="Repeat your password"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((visible) => !visible)}
              className="absolute inset-y-0 right-3 flex items-center text-asphalt-400 hover:text-signal-blue transition-colors"
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
              title={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? <Eye size={16} strokeWidth={1.8} /> : <EyeOff size={16} strokeWidth={1.8} />}
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
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>

          <div className="mt-4 flex flex-col items-center gap-2 text-xs">
            <p className="text-asphalt-400">
              Already have an account?{' '}
              <Link to="/login" className="text-signal-blue hover:underline">
                Sign in
              </Link>
            </p>
            <button
              type="button"
              onClick={handleUseDifferentEmail}
              className="text-asphalt-500 hover:text-asphalt-300 hover:underline"
            >
              Not {email}? Use a different email
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}