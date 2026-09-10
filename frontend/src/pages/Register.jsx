import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
<<<<<<< HEAD
  const { requestVerification } = useAuth();
=======
  const { register, verifiedEmail, clearEmailVerification } = useAuth();
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
  const navigate = useNavigate();
  const location = useLocation();
  const email = verifiedEmail || location.state?.email || '';

  const [form, setForm] = useState({
<<<<<<< HEAD
    email: '',
=======
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
  });
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

<<<<<<< HEAD
    setIsSubmitting(true);
    try {
      await requestVerification(form.email);
      navigate('/verify-email', {
        state: {
          email: form.email,
        },
      });
    } catch (err) {
      setError(err.message || 'Unable to send verification code. Please try again.');
=======
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
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
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
<<<<<<< HEAD
              Enter your email to receive a verification code. After verification, you can complete your account details and password.
=======
              Your email <span className="text-asphalt-200">{email}</span> is verified. Finish setting up your account below.
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
            </p>
          </div>

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
<<<<<<< HEAD
            name="email"
            type="email"
            required
            value={form.email}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="you@traffic.gov"
=======
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
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={6}
            value={form.password}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="At least 6 characters"
          />

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="confirmPassword">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            required
            minLength={6}
            value={form.confirmPassword}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="Repeat your password"
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
          />

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
<<<<<<< HEAD
            {isSubmitting ? 'Sending verification…' : 'Send verification code'}
=======
            {isSubmitting ? 'Creating account\u2026' : 'Create account'}
>>>>>>> a261d7631cd7a3411cce6a99d7d84368c407591c
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
