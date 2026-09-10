import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, verifyEmail } = useAuth();

  const [otp, setOtp] = useState('');
  const [accountForm, setAccountForm] = useState({
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const email = location.state?.email || '';

  function handleAccountChange(event) {
    const { name, value } = event.target;
    setAccountForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleOtpSubmit(event) {
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
      setOtpVerified(true);
    } catch (err) {
      setError(err.message || 'Unable to verify your email. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAccountSubmit(event) {
    event.preventDefault();
    setError('');

    if (!accountForm.name.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (accountForm.password !== accountForm.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (accountForm.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    const trimmedPhone = accountForm.phone ? accountForm.phone.trim() : '';
    let validatedPhone = null;

    if (trimmedPhone) {
      const cleanedPhone = trimmedPhone.replace(/[\s\-()]/g, '');
      const phoneRegex = /^(\+91[\-\s]?|0)?[6-9]\d{9}$|^[0-9]{10}$/;
      if (!phoneRegex.test(cleanedPhone)) {
        setError('Please enter a valid 10-digit phone number (e.g. 9876543210).');
        return;
      }
      validatedPhone = cleanedPhone;
    }

    setIsSubmitting(true);
    try {
      await register({
        name: accountForm.name.trim(),
        email,
        phone: validatedPhone,
        password: accountForm.password,
      });
      navigate('/login', { state: { verified: true } });
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
          <div className="inline-flex items-center justify-center gap-2 mb-3" />
          <h1 className="text-xl font-bold tracking-tight text-asphalt-100">
            Smart Traffic Monitoring &amp; Incident Analytics
          </h1>
        </div>

        <form
          onSubmit={otpVerified ? handleAccountSubmit : handleOtpSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6 shadow-xl"
        >
          <div className="mb-5 border-b border-asphalt-800 pb-3">
            <h2 className="text-sm font-semibold text-asphalt-100">
              {otpVerified ? 'Complete your account setup' : 'Verify your email'}
            </h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              {otpVerified
                ? `Your email ${email} has been verified. Finish creating your account below.`
                : `Enter the 6-digit code sent to ${email || 'your email'}.`}
            </p>
          </div>

          {!otpVerified && (
            <>
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
            </>
          )}

          {otpVerified && (
            <>
              <label className="block text-xs font-medium text-asphalt-300" htmlFor="name">
                Full Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                value={accountForm.name}
                onChange={handleAccountChange}
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
                value={accountForm.phone}
                onChange={handleAccountChange}
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
                value={accountForm.password}
                onChange={handleAccountChange}
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
                value={accountForm.confirmPassword}
                onChange={handleAccountChange}
                className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
                placeholder="Repeat your password"
              />
            </>
          )}

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
            {isSubmitting
              ? otpVerified
                ? 'Creating account…'
                : 'Verifying…'
              : otpVerified
                ? 'Create account'
                : 'Verify Email'}
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
