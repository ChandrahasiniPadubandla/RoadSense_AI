import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Wraps routes that must not be reachable until the visitor has verified
 * an email address via OTP (currently /login and /register).
 *
 * Enforced purely as a routing/UX gate on the frontend — the backend is
 * still the real authority (it independently checks is_email_verified on
 * both /auth/login and /auth/register), so this guard cannot be bypassed
 * to actually log in or create an account.
 *
 * Usage: <Route element={<RequireVerifiedEmail />}> ... </Route>
 */
export default function RequireVerifiedEmail() {
  const { isEmailVerified } = useAuth();
  const location = useLocation();

  if (!isEmailVerified) {
    return <Navigate to="/verify-email" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
