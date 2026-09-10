import React, { createContext, useContext, useEffect, useState } from 'react';
import { loginUser, logoutUser, registerUser, requestEmailVerification, verifyEmailUser } from '../api_services';

const AuthContext = createContext(null);
const VERIFIED_EMAIL_KEY = 'verifiedEmail';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('currentUser');
      const token = localStorage.getItem('accessToken');
      return stored && token ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [verifiedEmail, setVerifiedEmailState] = useState(() => {
    try {
      return localStorage.getItem(VERIFIED_EMAIL_KEY) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      const storedUser = localStorage.getItem('currentUser');
      const token = localStorage.getItem('accessToken');
      if (storedUser && token) {
        setUser(JSON.parse(storedUser));
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    }
    setIsLoading(false);
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
