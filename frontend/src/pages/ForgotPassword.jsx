import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { forgotPassword, resetPassword } from '../api_services';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isResetComplete, setIsResetComplete] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  async function requestOtp(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    setIsSending(true);
    try {
      const response = await forgotPassword(email);
      setMessage(response?.message || 'A reset code has been sent to your email.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Unable to send the reset code.');
    } finally {
      setIsSending(false);
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    setIsResetting(true);
    try {
      const response = await resetPassword({
        email,
        otp,
        newPassword,
      });
      setMessage(response?.message || 'Password reset successful.');
      setIsResetComplete(true);
      setOtp('');
      setNewPassword('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Unable to reset the password.');
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="text-sm font-semibold tracking-tight text-asphalt-100">
            Reset your password
          </p>
          <p className="mt-1 text-xs text-asphalt-400">
            Request a code, then choose a new password.
          </p>
        </div>

        <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6">
          {!isResetComplete ? (
            <>
              <form onSubmit={requestOtp}>
                <label className="block text-xs text-asphalt-400" htmlFor="reset-email">
                  Email
                </label>
                <input
                  id="reset-email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
                  placeholder="you@traffic.gov"
                />
                <button
                  type="submit"
                  disabled={isSending}
                  className="w-full rounded-md border border-signal-blue py-2 text-sm font-medium text-signal-blue transition-opacity hover:opacity-80 disabled:opacity-50"
                >
                  {isSending ? 'Sending...' : 'Send reset code'}
                </button>
              </form>

              <form onSubmit={handleResetPassword} className="mt-6 border-t border-asphalt-700 pt-6">
                <label className="block text-xs text-asphalt-400" htmlFor="reset-otp">
                  Reset code
                </label>
                <input
                  id="reset-otp"
                  type="text"
                  inputMode="numeric"
                  required
                  value={otp}
                  onChange={(event) => setOtp(event.target.value)}
                  className="mt-1 mb-4 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
                  placeholder="6-digit code"
                />

                <label className="block text-xs text-asphalt-400" htmlFor="new-password">
                  New password
                </label>
                <div className="relative mt-1 mb-4">
                  <input
                    id="new-password"
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    className="w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 pr-10 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
                    placeholder="At least 8 characters"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((visible) => !visible)}
                    className="absolute inset-y-0 right-3 flex items-center text-asphalt-400 hover:text-signal-blue transition-colors"
                    aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                    title={showNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showNewPassword ? <Eye size={16} strokeWidth={1.8} /> : <EyeOff size={16} strokeWidth={1.8} />}
                  </button>
                </div>

                {error && (
                  <p className="mb-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
                    {error}
                  </p>
                )}
                {message && (
                  <p className="mb-4 rounded-md border border-signal-green/40 bg-signal-green/10 px-3 py-2 text-xs text-signal-green">
                    {message}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isResetting}
                  className="w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {isResetting ? 'Resetting...' : 'Reset password'}
                </button>
              </form>
            </>
          ) : (
            <div>
              <p className="mb-4 rounded-md border border-signal-green/40 bg-signal-green/10 px-3 py-2 text-xs text-signal-green">
                {message}
              </p>
              <Link
                to="/login"
                className="block w-full rounded-md bg-signal-blue py-2 text-center text-sm font-medium text-white transition-opacity hover:opacity-90"
              >
                Back to sign in
              </Link>
            </div>
          )}
        </div>

        {!isResetComplete && (
          <p className="mt-5 text-center text-xs text-asphalt-400">
            <Link to="/login" className="text-signal-blue hover:underline">
              Back to sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}