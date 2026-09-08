import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Wraps routes that only specific roles may access.
 * Usage: <Route element={<RoleRoute allow={['SUPER_ADMIN']} />}> ... </Route>
 */
export default function RoleRoute({ allow }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  if (!allow.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
