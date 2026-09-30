import React, { createContext, useContext, useEffect, useState } from 'react';
import { loginUser, logoutUser, registerUser, requestEmailVerification, verifyEmailUser, getCurrentUser } from '../api_services';

const AuthContext = createContext(null);
const VERIFIED_EMAIL_KEY = 'verifiedEmail';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('currentUser');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
    const saved = typeof window !== 'undefined' ? localStorage.getItem('currentUser') : null;
    return !!token && !saved;
  });
  const [verifiedEmail, setVerifiedEmailState] = useState(() => {
    try {
      return localStorage.getItem(VERIFIED_EMAIL_KEY) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    let active = true;
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setIsLoading(false);
      return () => { active = false; };
    }

    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((error) => {
        // Keep a still-possibly-valid token if the backend is temporarily offline.
        // 401/404 responses indicate an invalid session; the interceptor clears 401s.
        if (error.response?.status === 401 || error.response?.status === 404) {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('currentUser');
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => { active = false; };
  }, []);

  useEffect(() => {
    function clearUnauthorizedSession() {
      setUser(null);
    }
    window.addEventListener('auth:unauthorized', clearUnauthorizedSession);
    return () => window.removeEventListener('auth:unauthorized', clearUnauthorizedSession);
  }, []);

  async function login(email, password) {
    const res = await loginUser(email, password);
    setUser(res.user);
    return res.user;
  }

  async function logout() {
    await logoutUser();
    setUser(null);
  }

  async function register(userData) {
    return registerUser(userData);
  }

  async function requestVerification(email) {
    return requestEmailVerification(email);
  }

  async function verifyEmail(email, otp) {
    const result = await verifyEmailUser(email, otp);

    markEmailVerified(email);
    return result;
  }

  function markEmailVerified(email) {
    try {
      localStorage.setItem(VERIFIED_EMAIL_KEY, email);
    } catch {

    }
    setVerifiedEmailState(email);
  }

  function clearEmailVerification() {
    try {
      localStorage.removeItem(VERIFIED_EMAIL_KEY);
    } catch {
      // ignore
    }
    setVerifiedEmailState(null);
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    requestVerification,
    verifyEmail,
    logout,
    verifiedEmail,
    isEmailVerified: !!verifiedEmail,
    markEmailVerified,
    clearEmailVerification,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
