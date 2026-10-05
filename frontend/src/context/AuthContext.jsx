import React, {
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react';

import {
  loginUser,
  logoutUser,
  registerUser,
  requestEmailVerification,
  verifyEmailUser,
  getCurrentUser,
  updateMyProfile,
} from '../api_services';

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
    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem('accessToken')
        : null;

    const saved =
      typeof window !== 'undefined'
        ? localStorage.getItem('currentUser')
        : null;

    return !!token && !saved;
  });

  const [verifiedEmail, setVerifiedEmailState] = useState(() => {
    try {
      return localStorage.getItem(VERIFIED_EMAIL_KEY) || null;
    } catch {
      return null;
    }
  });

  // --------------------------------------------------
  // Get current user when the application starts
  // --------------------------------------------------
  useEffect(() => {
    let active = true;

    const token = localStorage.getItem('accessToken');

    if (!token) {
      setIsLoading(false);

      return () => {
        active = false;
      };
    }

    getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch((error) => {
        if (
          error.response?.status === 401 ||
          error.response?.status === 404
        ) {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('currentUser');

          if (active) {
            setUser(null);
          }
          if (active) setUser(null);

        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // --------------------------------------------------
  // Handle unauthorized API responses
  // --------------------------------------------------
  useEffect(() => {
    function clearUnauthorizedSession() {
      setUser(null);
    }

    window.addEventListener(
      'auth:unauthorized',
      clearUnauthorizedSession
    );

    return () => {
      window.removeEventListener(
        'auth:unauthorized',
        clearUnauthorizedSession
      );
    };
  }, []);

  // --------------------------------------------------
  // Login
  // --------------------------------------------------
  async function login(email, password) {
    const res = await loginUser(email, password);

    setUser(res.user);

    return res.user;
  }

  // --------------------------------------------------
  // Logout
  // --------------------------------------------------
  async function logout() {
    await logoutUser();

    setUser(null);
  }

  // --------------------------------------------------
  // Register
  // --------------------------------------------------
  async function register(userData) {
    return registerUser(userData);
  }

  // --------------------------------------------------
  // Email verification
  // --------------------------------------------------
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
      localStorage.setItem(
        VERIFIED_EMAIL_KEY,
        email
      );
    } catch {}

    setVerifiedEmailState(email);
  }

  function clearEmailVerification() {
    try {
      localStorage.removeItem(
        VERIFIED_EMAIL_KEY
      );
    } catch {}

    setVerifiedEmailState(null);
  }

  // --------------------------------------------------
  // UPDATE CURRENT USER PROFILE
  // --------------------------------------------------
  async function updateProfile(profileData) {
    const updatedUser = await updateMyProfile(profileData);

    // Update React state
    setUser(updatedUser);

    // Keep localStorage synchronized
    try {
      localStorage.setItem(
        'currentUser',
        JSON.stringify(updatedUser)
      );
    } catch {}

    return updatedUser;
  }

  // --------------------------------------------------
  // Context value
  // --------------------------------------------------
  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,

    login,
    register,
    logout,

    requestVerification,
    verifyEmail,

    verifiedEmail,
    isEmailVerified: !!verifiedEmail,

    markEmailVerified,
    clearEmailVerification,

    // Profile
    updateProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error(
      'useAuth must be used within an AuthProvider'
    );
  }

  return ctx;
}