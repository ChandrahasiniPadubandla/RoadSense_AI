import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const { requestVerification } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

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
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center justify-center gap-2 mb-3" />
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
              Enter your email to receive a verification code. After verification, you can complete your account details and password.
            </p>
          </div>

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            value={form.email}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="you@traffic.gov"
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
            {isSubmitting ? 'Sending verification…' : 'Send verification code'}
          </button>

          <p className="mt-4 text-center text-xs text-asphalt-400">
            Already have an account?{' '}
            <Link to="/login" className="text-signal-blue hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
