import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const RESEND_COOLDOWN_SECONDS = 30;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const { requestVerification, verifyEmail, isEmailVerified, verifiedEmail } = useAuth();

  const [step, setStep] = useState(isEmailVerified ? 'done' : 'email');
  const [email, setEmail] = useState(verifiedEmail || location.state?.email || '');
  const [otp, setOtp] = useState('');

  const [fieldError, setFieldError] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const cooldownTimerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);
    };
  }, []);

  function startCooldown() {
    setCooldown(RESEND_COOLDOWN_SECONDS);
    if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);
    cooldownTimerRef.current = setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          clearInterval(cooldownTimerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  async function handleSendOtp(event) {
    event.preventDefault();
    setFieldError('');
    setError('');
    setInfo('');

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setFieldError('Please enter your email address.');
      return;
    }
    if (!EMAIL_REGEX.test(trimmedEmail)) {
      setFieldError('Please enter a valid email address.');
      return;
    }

    setIsSendingOtp(true);
    try {
      await requestVerification(trimmedEmail);
      setEmail(trimmedEmail);
      setStep('otp');
      setInfo(`We\u2019ve sent a 6-digit verification code to ${trimmedEmail}.`);
      startCooldown();
    } catch (err) {
      setError(err.message || 'Unable to send the verification code. Please try again.');
    } finally {
      setIsSendingOtp(false);
    }
  }

  async function handleVerifyOtp(event) {
    event.preventDefault();
    setFieldError('');
    setError('');

    if (!otp) {
      setFieldError('Please enter the verification code.');
      return;
    }
    if (!/^\d{6}$/.test(otp)) {
      setFieldError('The verification code must be exactly 6 digits.');
      return;
    }

    setIsVerifying(true);
    try {
      await verifyEmail(email, otp);
      setInfo('');
      setStep('done');
    } catch (err) {
      setError(err.message || 'Unable to verify the code. Please try again.');
    } finally {
      setIsVerifying(false);
    }
  }

  async function handleResendOtp() {
    if (cooldown > 0 || isResending) return;
    setError('');
    setInfo('');
    setIsResending(true);
    try {
      await requestVerification(email);
      setInfo('A new verification code has been sent to your email.');
      startCooldown();
    } catch (err) {
      setError(err.message || 'Unable to resend the verification code. Please try again.');
    } finally {
      setIsResending(false);
    }
  }

  function handleUseDifferentEmail() {
    setStep('email');
    setOtp('');
    setError('');
    setInfo('');
    setFieldError('');
    setCooldown(0);
    if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-bold tracking-tight text-asphalt-100">
            Smart Traffic Monitoring &amp; Incident Analytics
          </h1>
        </div>

        <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6 shadow-xl">
          {step === 'email' && (
            <form onSubmit={handleSendOtp}>
              <div className="mb-5 border-b border-asphalt-800 pb-3">
                <h2 className="text-sm font-semibold text-asphalt-100">Verify Your Email</h2>
                <p className="mt-0.5 text-xs text-asphalt-400">
                  Enter your email address to receive a verification OTP.
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
                autoFocus
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-1 mb-1 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
                placeholder="you@traffic.gov"
              />
              {fieldError && <p className="mb-4 mt-1 text-xs text-signal-red">{fieldError}</p>}
              {!fieldError && <div className="mb-4" />}

              {error && (
                <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={isSendingOtp}
                className="w-full rounded-md bg-signal-blue py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {isSendingOtp ? 'Sending OTP\u2026' : 'Send OTP'}
              </button>

              <p className="mt-4 text-center text-xs text-asphalt-400">
                Already verified?{' '}
                <Link to="/login" className="text-signal-blue hover:underline">
                  Go to sign in
                </Link>
              </p>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={handleVerifyOtp}>
              <div className="mb-5 border-b border-asphalt-800 pb-3">
                <h2 className="text-sm font-semibold text-asphalt-100">Enter Verification Code</h2>
                <p className="mt-0.5 text-xs text-asphalt-400">
                  Enter the 6-digit code sent to <span className="text-asphalt-200">{email}</span>.
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
                autoFocus
                value={otp}
                onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                className="mt-1 mb-1 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-center text-lg tracking-[0.5em] text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
                placeholder="123456"
              />
              {fieldError && <p className="mb-4 mt-1 text-xs text-signal-red">{fieldError}</p>}
              {!fieldError && <div className="mb-4" />}

              {info && (
                <p className="mb-4 rounded-md border border-signal-green/40 bg-signal-green/10 px-3 py-2 text-xs text-signal-green">
                  {info}
                </p>
              )}
              {error && (
                <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={isVerifying}
                className="w-full rounded-md bg-signal-blue py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {isVerifying ? 'Verifying\u2026' : 'Verify OTP'}
              </button>

              <div className="mt-4 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handleUseDifferentEmail}
                  className="text-asphalt-400 hover:text-asphalt-200 hover:underline"
                >
                  Use a different email
                </button>

                {cooldown > 0 ? (
                  <span className="text-asphalt-500">Resend OTP in {cooldown}s</span>
                ) : (
                  <button
                    type="button"
                    onClick={handleResendOtp}
                    disabled={isResending}
                    className="text-signal-blue hover:underline disabled:opacity-50"
                  >
                    {isResending ? 'Resending\u2026' : 'Resend OTP'}
                  </button>
                )}
              </div>
            </form>
          )}

          {step === 'done' && (
            <div>
              <div className="mb-5 border-b border-asphalt-800 pb-3">
                <h2 className="text-sm font-semibold text-asphalt-100">Email Verified</h2>
                <p className="mt-0.5 text-xs text-asphalt-400">
                  <span className="text-asphalt-200">{email || verifiedEmail}</span> has been verified successfully.
                </p>
              </div>

              <p className="mb-4 rounded-md border border-signal-green/40 bg-signal-green/10 px-3 py-2 text-xs text-signal-green">
                You can now sign in or create your account.
              </p>

              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/register', { state: { email: email || verifiedEmail } })}
                  className="w-full rounded-md bg-signal-blue py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
                >
                  Continue to Sign Up
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  className="w-full rounded-md border border-asphalt-600 py-2.5 text-sm font-medium text-asphalt-200 transition-colors hover:border-signal-blue hover:text-signal-blue"
                >
                  Continue to Login
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
