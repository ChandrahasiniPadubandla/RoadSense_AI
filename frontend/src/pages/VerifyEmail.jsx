import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const { verifyEmail } = useAuth();

  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const email = location.state?.email || '';

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!email) {
      setError('Missing registration email. Please register again.');
      return;
    }

    if (otp.length !== 6) {
      setError('Please enter a valid 6-digit OTP code.');
      return;
    }

    setIsSubmitting(true);
    try {
      await verifyEmail(email, otp);
      navigate('/login', { state: { verified: true } });
    } catch (err) {
      setError(err.message || 'Unable to verify your email. Please try again.');
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
            <h2 className="text-sm font-semibold text-asphalt-100">Verify your email</h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              Enter the 6-digit code sent to {email || 'your email'}.
            </p>
          </div>

          <label className="block text-xs font-medium text-asphalt-300" htmlFor="otp">
            Verification Code
          </label>
          <input
            id="otp"
            name="otp"
            type="text"
            inputMode="numeric"
            maxLength={6}
            required
            value={otp}
            onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="123456"
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
            {isSubmitting ? 'Verifying…' : 'Verify Email'}
          </button>

          <p className="mt-4 text-center text-xs text-asphalt-400">
            Already verified?{' '}
            <Link to="/login" className="text-signal-blue hover:underline">
              Go to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
