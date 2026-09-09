import React, { createContext, useContext, useEffect, useState } from 'react';
import { loginUser, logoutUser, registerUser, verifyEmailUser } from '../api_services';

const AuthContext = createContext(null);

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

  // Restore session on page reload
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

  async function verifyEmail(email, otp) {
    return verifyEmailUser(email, otp);
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    verifyEmail,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
