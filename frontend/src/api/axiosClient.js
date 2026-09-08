import axios from 'axios';

// -----------------------------------------------------------------------
// Single place that knows how to talk to the backend.
// Every service file (trafficService, accidentService, ...) imports this
// instead of calling axios directly, so auth headers, base URL, and error
// handling live in exactly one place.
// -----------------------------------------------------------------------

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

export const USE_MOCK_DATA =
  (import.meta.env.VITE_USE_MOCK_DATA ?? 'false') === 'true';

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT to every outgoing request, once the backend issues one.
axiosClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Central place to react to auth failures (expired/invalid token).
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('currentUser');
      // Avoid a hard redirect loop if we're already on /login
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
