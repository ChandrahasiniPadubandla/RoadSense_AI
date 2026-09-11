import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, CheckCircle2, Mail } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PHONE_REGEX = /^(\+91[\-\s]?|0)?[6-9]\d{9}$|^[0-9]{10}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Register() {
  const { register, requestVerification, verifyEmail, verifiedEmail, markEmailVerified, clearEmailVerification } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState(verifiedEmail || location.state?.email || '');
  const [isEmailVerified, setIsEmailVerified] = useState(!!(verifiedEmail || location.state?.verified));

  // Inline OTP states
  const [otp, setOtp] = useState('');
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [otpMessage, setOtpMessage] = useState('');
  const [otpError, setOtpError] = useState('');
  const [countdown, setCountdown] = useState(0);

  // Form states
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

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (error) setError('');
  }

  // Step 1: Send verification code to email
  async function handleSendOtp() {
    setOtpError('');
    setOtpMessage('');
    setError('');

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Please enter your email address first.');
      return;
    }

    if (!EMAIL_REGEX.test(cleanEmail)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsSendingOtp(true);
    try {
      await requestVerification(cleanEmail);
      setIsOtpSent(true);
      setCountdown(60);
      setOtpMessage(`Verification code sent to ${cleanEmail}. Please check your inbox.`);
    } catch (err) {
      setError(err.message || 'Unable to send verification code. Please check the email.');
    } finally {
      setIsSendingOtp(false);
    }
  }

  // Step 2: Verify the 6-digit OTP code inline
  async function handleVerifyOtp() {
    setOtpError('');
    setOtpMessage('');
    setError('');

    if (otp.length !== 6) {
      setOtpError('Please enter the full 6-digit code.');
      return;
    }

    setIsVerifyingOtp(true);
    try {
      await verifyEmail(email.trim(), otp);
      setIsEmailVerified(true);
      setIsOtpSent(false);
      setOtp('');
      markEmailVerified(email.trim());
      setOtpMessage('');
    } catch (err) {
      setOtpError(err.message || 'Invalid or expired verification code.');
    } finally {
      setIsVerifyingOtp(false);
    }
  }

  // Option to change email if already verified or wrong
  function handleResetEmail() {
    setIsEmailVerified(false);
    setIsOtpSent(false);
    setOtp('');
    setOtpError('');
    setOtpMessage('');
    clearEmailVerification();
  }

  // Final submit: Create user account
  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!isEmailVerified) {
      setError('Please verify your email address before creating an account.');
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
        email: email.trim(),
        phone: validatedPhone,
        password: form.password,
      });
      clearEmailVerification();
      navigate('/login', { state: { registered: true, email: email.trim() } });
    } catch (err) {
      setError(err.message || 'Unable to create your account. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-bold tracking-tight text-asphalt-100">
            Smart Traffic Monitoring &amp; Incident Analytics
          </h1>
          <p className="mt-1 text-xs text-asphalt-400">
            RoadSense AI Real-Time Traffic &amp; Safety Platform
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6 shadow-xl"
        >
          <div className="mb-5 border-b border-asphalt-800 pb-3">
            <h2 className="text-sm font-semibold text-asphalt-100">Create your account</h2>
            <p className="mt-0.5 text-xs text-asphalt-400">
              {isEmailVerified
                ? 'Email verified! Complete your details below to finish setup.'
                : 'Enter your email and verify it with a one-time code to get started.'}
            </p>
          </div>

          {/* Email & Inline Verification Section */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-asphalt-300" htmlFor="email">
              Email Address
            </label>
            <div className="mt-1 flex gap-2">
              <input
                id="email"
                type="email"
                required
                disabled={isEmailVerified}
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError('');
                }}
                placeholder="you@example.com"
                className={`w-full rounded-md border ${
                  isEmailVerified
                    ? 'border-signal-green/60 bg-asphalt-800/70 text-asphalt-200 cursor-not-allowed'
                    : 'border-asphalt-600 bg-asphalt-800 text-asphalt-100 focus:border-signal-blue'
                } px-3 py-2 text-sm outline-none transition-colors`}
              />
              {!isEmailVerified ? (
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={!email.trim() || isSendingOtp || countdown > 0}
                  className="shrink-0 rounded-md bg-signal-blue px-3.5 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {isSendingOtp ? 'Sending…' : isOtpSent ? 'Resend' : 'Verify'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleResetEmail}
                  className="shrink-0 rounded-md border border-asphalt-700 bg-asphalt-800 px-3 py-2 text-xs font-medium text-asphalt-300 hover:text-signal-blue hover:border-signal-blue transition-colors"
                  title="Change email"
                >
                  Change
                </button>
              )}
            </div>

            {/* Verification Status Badge */}
            {isEmailVerified && (
              <div className="mt-1.5 flex items-center gap-1.5 text-xs text-signal-green">
                <CheckCircle2 size={14} className="shrink-0" />
                <span className="font-medium">Email verified successfully</span>
              </div>
            )}

            {/* Inline OTP Input Box */}
            {!isEmailVerified && isOtpSent && (
              <div className="mt-2.5 rounded-lg border border-signal-blue/40 bg-signal-blue/10 p-3">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-medium text-asphalt-200" htmlFor="reg-otp">
                    Enter 6-digit Verification Code
                  </label>
                  {countdown > 0 && (
                    <span className="text-[11px] text-asphalt-400">Resend in {countdown}s</span>
                  )}
                </div>
                <div className="mt-1.5 flex gap-2">
                  <input
                    id="reg-otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="123456"
                    className="w-36 rounded-md border border-asphalt-600 bg-asphalt-900 px-3 py-1.5 text-center text-sm font-mono tracking-widest text-asphalt-100 outline-none focus:border-signal-blue"
                  />
                  <button
                    type="button"
                    onClick={handleVerifyOtp}
                    disabled={otp.length !== 6 || isVerifyingOtp}
                    className="rounded-md bg-signal-blue px-4 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {isVerifyingOtp ? 'Verifying…' : 'Verify Code'}
                  </button>
                </div>
                {otpMessage && (
                  <p className="mt-2 text-xs text-signal-green">{otpMessage}</p>
                )}
                {otpError && (
                  <p className="mt-2 text-xs text-signal-red">{otpError}</p>
                )}
              </div>
            )}
          </div>

          {/* Full Name */}
          <label className="block text-xs font-medium text-asphalt-300" htmlFor="name">
            Full Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            required
            value={form.name}
            onChange={handleChange}
            className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 placeholder-asphalt-500 outline-none transition-colors focus:border-signal-blue"
            placeholder="Enter your full name"
          />

          {/* Phone Number (Optional) */}
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

          {/* Password */}
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

          {/* Confirm Password */}
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

          {/* Error Banner */}
          {error && (
            <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          )}

          {/* Create Account Submit Button */}
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
              <Link to="/login" className="text-signal-blue hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}