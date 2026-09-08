import React, { createContext, useContext, useEffect, useState } from 'react';
import * as authService from '../api/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session on page reload
  useEffect(() => {
    const storedUser = localStorage.getItem('currentUser');
    const token = localStorage.getItem('accessToken');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  async function login(email, password) {
    const { accessToken, user: loggedInUser } = await authService.login(
      email,
      password
    );
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('currentUser', JSON.stringify(loggedInUser));
    setUser(loggedInUser);
    return loggedInUser;
  }

  async function logout() {
    await authService.logout();
    localStorage.removeItem('accessToken');
    localStorage.removeItem('currentUser');
    setUser(null);
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
