import axios from 'axios';

// -----------------------------------------------------------------------------
// Unified API Services for RoadSense AI
// Consolidates Dashboard Stats, Map Visualizations, Roads, and Auth API calls
// -----------------------------------------------------------------------------

// Base URL: reads from VITE_API_BASE_URL (defaults to http://127.0.0.1:8000)
const RAW_URL = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = RAW_URL?.replace(/\/api\/?$/, '') || 'http://192.168.0.62:8000';



// Single configured Axios instance

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach bearer token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 gracefully
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('currentUser');
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
    return Promise.reject(error);
  }
);

// -----------------------------------------------------------------------------
// 1. DASHBOARD APIS (NO DUMMY DATA — returns real data or null/empty)
// -----------------------------------------------------------------------------

/**
 * Fetch KPI statistics from /api/dashboard/stats (or /api/dashboard/summary)
 * Returns null if data is not available (NO dummy numbers).
 */
export async function getDashboardStats() {
  try {
    const { data } = await apiClient.get('/api/dashboard/stats');
    return {
      activeRoads: data.active_roads ?? 0,
      totalRoads: data.total_roads ?? 0,
      highTraffic: data.high_traffic_roads ?? data.high_traffic_records ?? 0,
      accidentAlerts: data.accident_alerts ?? data.active_alerts ?? 0,
      highRiskZones: data.high_risk_zones ?? 0,
      totalAccidents: data.total_accidents ?? 0,
      accidentsToday: data.accidents_today ?? 0,
      totalTrafficRecords: data.total_traffic_records ?? 0,
      averageSpeed: data.average_system_speed ?? 0,
      timestamp: data.timestamp || new Date().toISOString(),
    };
  } catch (error) {
    console.warn('API /api/dashboard/stats failed, trying /api/dashboard/summary:', error.message);
    try {
      const { data } = await apiClient.get('/api/dashboard/summary');
      return {
        activeRoads: data.active_roads ?? 0,
        totalRoads: data.total_roads ?? 0,
        highTraffic: data.high_traffic_roads ?? data.high_traffic_records ?? 0,
        accidentAlerts: data.active_alerts ?? data.accident_alerts ?? 0,
        highRiskZones: data.high_risk_zones ?? 0,
        totalAccidents: data.total_accidents ?? 0,
        accidentsToday: data.accidents_today ?? 0,
        totalTrafficRecords: data.total_traffic_records ?? 0,
        averageSpeed: data.average_system_speed ?? 0,
        timestamp: data.timestamp || new Date().toISOString(),
      };
    } catch (fallbackError) {
      console.error('All dashboard stats endpoints failed:', fallbackError);
      return null;
    }
  }
}

/**
 * Fetch traffic volume trend for line chart from /api/dashboard/trend
 * Returns empty array if no data exists (NO dummy trend points).
 */
export async function getDashboardTrend() {
  try {
    const { data } = await apiClient.get('/api/dashboard/trend');
    if (Array.isArray(data) && data.length > 0) {
      // Check if data is not just empty fallback records
      const hasRealObservations = data.some((d) => (d.vehicle_count || 0) > 0);
      if (hasRealObservations) {
        return data.map((item, idx) => {
          const timeStr = item.timestamp
            ? (item.timestamp.includes('T')
              ? item.timestamp.split('T')[1].slice(0, 5)
              : new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }))
            : `T-${idx}`;
          return {
            hour: timeStr,
            vehicles: item.vehicle_count ?? 0,
            speed: item.average_speed ? Math.round(item.average_speed) : 0,
            roadId: item.road_id,
          };
        });
      }
    }
    return [];
  } catch (error) {
    console.warn('Could not fetch /api/dashboard/trend:', error.message);
    return [];
  }
}

/**
 * Fetch roads list for dashboard table from /api/map/traffic-layer or /api/roads
 * Returns empty array if no roads found (NO dummy roads).
 */
export async function getRoads() {
  try {
    const { data: layer } = await apiClient.get('/api/map/traffic-layer');
    if (layer?.features && layer.features.length > 0) {
      return layer.features.map((f) => {
        const p = f.properties || {};
        return {
          id: p.road_id || f.id,
          name: p.road_name || 'Road Segment',
          roadType: p.road_type || 'Arterial',
          vehicleCount: p.vehicle_count != null ? p.vehicle_count : '-',
          avgSpeed: p.average_speed != null ? `${Math.round(p.average_speed)} km/h` : (p.speed_limit ? `${p.speed_limit} km/h` : '-'),
          weather: p.weather_condition || 'Clear',
          trafficLevel: p.congestion_level && p.congestion_level !== 'UNKNOWN' ? p.congestion_level.toUpperCase() : null,
          confidenceScore: p.confidence_score,
          isPredicted: p.is_predicted ?? false,
          capacityUtilization: p.capacity_utilization,
          lanes: p.number_of_lanes || 4,
          speedLimit: p.speed_limit,
          lat: f.geometry?.coordinates?.[0]?.[1],
          lng: f.geometry?.coordinates?.[0]?.[0],
        };
      });
    }
  } catch (err) {
    console.warn('Traffic layer fetch failed, falling back to /api/roads:', err.message);
  }

  try {
    const { data } = await apiClient.get('/api/roads');
    if (Array.isArray(data) && data.length > 0) {
      return data.map((road) => ({
        id: road.road_id,
        name: road.road_name,
        roadType: road.road_type,
        vehicleCount: '-',
        avgSpeed: road.speed_limit ? `${road.speed_limit} km/h` : '-',
        weather: road.road_condition || 'Clear',
        trafficLevel: null,
        lanes: road.number_of_lanes,
        speedLimit: road.speed_limit,
        lat: road.start_latitude,
        lng: road.start_longitude,
      }));
    }
  } catch (error) {
    console.error('Failed to fetch roads from backend:', error);
  }

  return [];
}

/** Fetch the newest traffic anomalies recorded by the ML service. */
export async function getAnomalies(limit = 20) {
  try {
    const { data } = await apiClient.get('/api/anomalies', { params: { limit } });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching traffic anomalies:', error);
    throw error;
  }
}

/** Run the trained anomaly model against supplied or road-derived telemetry. */
export async function predictAnomaly(payload) {
  const { data } = await apiClient.post('/api/anomalies/predict', payload);
  return data;
}

// -----------------------------------------------------------------------------
// 2. MAP VISUALIZATION APIS (Returns real GeoJSON or empty FeatureCollection)
// -----------------------------------------------------------------------------

/**
 * Fetch GeoJSON Traffic Roads Layer from /api/map/traffic-layer
 */
export async function getTrafficLayer() {
  try {
    const { data } = await apiClient.get('/api/map/traffic-layer');
    return data && Array.isArray(data.features) ? data : { type: 'FeatureCollection', features: [] };
  } catch (error) {
    console.error('Error fetching /api/map/traffic-layer:', error);
    return { type: 'FeatureCollection', features: [] };
  }
}

/**
 * Fetch GeoJSON Accident Incidents Layer from /api/map/accident-layer
 */
export async function getAccidentLayer(days = null, severity = null) {
  try {
    const params = {};
    if (days) params.days = days;
    if (severity) params.severity = severity;
    const { data } = await apiClient.get('/api/map/accident-layer', { params });
    return data && Array.isArray(data.features) ? data : { type: 'FeatureCollection', features: [] };
  } catch (error) {
    console.error('Error fetching /api/map/accident-layer:', error);
    return { type: 'FeatureCollection', features: [] };
  }
}

/**
 * Fetch GeoJSON Hotspots / Hazard Zones from /api/map/hotspots-layer
 */
export async function getHotspotsLayer() {
  try {
    const { data } = await apiClient.get('/api/map/hotspots-layer');
    return data && Array.isArray(data.features) ? data : { type: 'FeatureCollection', features: [] };
  } catch (error) {
    console.error('Error fetching /api/map/hotspots-layer:', error);
    return { type: 'FeatureCollection', features: [] };
  }
}

/**
 * Fetch GeoJSON Traffic Anomalies from /api/map/anomalies-layer
 */
export async function getAnomaliesLayer() {
  try {
    const { data } = await apiClient.get('/api/map/anomalies-layer');
    return data && Array.isArray(data.features) ? data : { type: 'FeatureCollection', features: [] };
  } catch (error) {
    console.error('Error fetching /api/map/anomalies-layer:', error);
    return { type: 'FeatureCollection', features: [] };
  }
}

// -----------------------------------------------------------------------------
// 3. AUTHENTICATION APIS
// -----------------------------------------------------------------------------

export async function loginUser(email, password) {
  try {
    const { data } = await apiClient.post('/auth/login', { email, password });
    const token = data.access_token || data.accessToken;
    if (token) {
      localStorage.setItem('accessToken', token);
    }
    const user = normalizeAuthUser(data.user, email);
    localStorage.setItem('currentUser', JSON.stringify(user));
    return { accessToken: token, user };
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || 'Login failed';
    throw new Error(msg);
  }
}

function normalizeAuthUser(user, fallbackEmail = '') {
  const rawRole = user?.role_name ?? user?.role ?? '';

  return {
    id: user?.user_id || user?.id,
    username: user?.username || '',
    email: user?.email || fallbackEmail,
    name: user?.name || fallbackEmail.split('@')[0] || '',
    phone: user?.phone ?? user?.mobile ?? user?.phone_number ?? '',
    role:
      typeof rawRole === 'string'
        ? rawRole.toUpperCase()
        : rawRole?.role_name
          ? rawRole.role_name.toUpperCase()
          : '',
  };
}
export async function updateMyProfile(payload) {
  const response = await apiClient.put('/auth/me', payload);

  const updatedUser = normalizeAuthUser(response.data);

  try {
    localStorage.setItem(
      'currentUser',
      JSON.stringify(updatedUser)
    );
  } catch {}

  return updatedUser;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get('/auth/me');
  const user = normalizeAuthUser(data);
  localStorage.setItem('currentUser', JSON.stringify(user));
  return user;
}

export async function registerUser({ name, email, password, phone = null }) {
  try {
    const { data } = await apiClient.post('/auth/register', {
      name,
      email,
      password,
      phone,
    });
    return data;
  } catch (error) {
    const detail = error.response?.data?.detail;
    let msg = 'Registration failed';
    if (Array.isArray(detail)) {
      msg = detail
        .map((d) => (d.msg ? d.msg.replace(/^Value error,\s*/i, '') : JSON.stringify(d)))
        .join(', ');
    } else if (typeof detail === 'string') {
      msg = detail;
    } else if (error.message) {
      msg = error.message;
    }
    throw new Error(msg);
  }
}

/**
 * Send a 6-digit OTP to the given email address via
 * POST /auth/request-email-verification. Used both for the initial
 * "Send OTP" action and for "Resend OTP" on the verify-email page.
 */
export async function requestEmailVerification(email) {
  try {
    const { data } = await apiClient.post('/auth/request-email-verification', { email });
    return data;
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || 'Unable to send verification code';
    throw new Error(msg);
  }
}

export async function verifyEmailUser(email, otp) {
  try {
    const { data } = await apiClient.post('/auth/verify-email', { email, otp });
    return data;
  } catch (error) {
    const msg = error.response?.data?.detail || error.message || 'Email verification failed';
    throw new Error(msg);
  }
}

export async function forgotPassword(email) {
  const { data } = await apiClient.post('/auth/forgot-password', { email });
  return data;
}

export async function resetPassword({ email, otp, newPassword }) {
  const { data } = await apiClient.post('/auth/reset-password', {
    email,
    otp,
    new_password: newPassword,
  });
  return data;
}

export async function logoutUser() {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('currentUser');
}

// -----------------------------------------------------------------------------
// 4. CHATBOT API (Previous bot backend functionality)
// -----------------------------------------------------------------------------

/**
 * Send chatbot query to backend /api/chatbot/message
 * Handles message and history formatted as expected by the backend
 */
export async function sendChatbotMessage(message, history = []) {
  const payload = {
    message,
    history: history.map((h) => ({
      role: h.role === 'user' ? 'user' : 'assistant',
      content: h.content || h.text || '',
    })),
  };

  const response = await apiClient.post('/api/chatbot/message', payload);
  return response.data; // { reply: string, mode: "openai" | "local-fallback" }
}

// -----------------------------------------------------------------------------
// 5. AI ROUTE PREDICTION APIS (User start & end location triggers)
// -----------------------------------------------------------------------------

/**
 * Predict traffic congestion for start & end locations
 * Returns { congestion_level, estimated_time, distance_km, weather_conditions, road_conditions, ml_features }
 */
export async function predictRouteTraffic(payload) {
  const { data } = await apiClient.post('/api/predictions/traffic/route', payload);
  return data;
}

/**
 * Predict accident risk for start & end locations
 * Returns { risk_percentage, risk_level, distance_km, weather_conditions, road_conditions, ml_features }
 */
export async function predictRouteAccident(payload) {
  const { data } = await apiClient.post('/api/predictions/accidents/route', payload);
  return data;
}

/**
 * Fetch the latest stored accident risk prediction per road.
 * GET /api/predictions/accidents/latest -> AccidentPredictionResponse[]
 */
export async function getLatestAccidentPredictions() {
  try {
    const { data } = await apiClient.get('/api/predictions/accidents/latest');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/predictions/accidents/latest:', error);
    return [];
  }
}

// -----------------------------------------------------------------------------
// 6. TRAFFIC PREDICTION APIS (single road, on-demand — DPR Module 3)
// -----------------------------------------------------------------------------

/**
 * Run the traffic congestion prediction model for a single road on-demand.
 * POST /api/predictions/traffic/predict
 * Body matches TrafficPredictionRunRequest exactly (backend/app/schemas/prediction.py):
 *   { road_id (required), target_minutes_ahead?, vehicle_count?, average_speed?,
 *     traffic_density?, weather?, rainfall?, temperature?, road_condition?,
 *     is_holiday?, persist? }
 * Returns TrafficPredictionRunResponse:
 *   { prediction_id, road_id, road_name, congestion_level, estimated_time,
 *     target_time, predicted_congestion, predicted_vehicle_count,
 *     confidence_score, class_probabilities, created_at }
 */
export async function predictTraffic(payload) {
  const { data } = await apiClient.post('/api/predictions/traffic/predict', payload);
  return data;
}

/**
 * Fetch the latest stored traffic congestion prediction per road.
 * GET /api/predictions/traffic/latest -> TrafficPredictionResponse[]
 */
export async function getLatestTrafficPredictions() {
  try {
    const { data } = await apiClient.get('/api/predictions/traffic/latest');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/predictions/traffic/latest:', error);
    return [];
  }
}

// -----------------------------------------------------------------------------
// 7. CRUD SERVICES (Zones, Accidents, Emergency, Alerts, Admin)
// -----------------------------------------------------------------------------

export async function getZones() {
  try {
    const { data } = await apiClient.get('/api/zones');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/zones:', error);
    return [];
  }
}

export async function getAccidents(params = {}) {
  try {
    const { data } = await apiClient.get('/api/accidents', { params });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/accidents:', error);
    return [];
  }
}

export async function createAccident(payload) {
  const { data } = await apiClient.post('/api/accidents', payload);
  return data;
}

export async function getEmergencyResponses(params = {}) {
  const { data } = await apiClient.get('/api/emergency', { params });
  return Array.isArray(data) ? data : [];
}

export async function createEmergencyResponse(payload) {
  const { data } = await apiClient.post('/api/emergency', payload);
  return data;
}

export async function updateEmergencyResponse(responseId, payload) {
  const { data } = await apiClient.patch(`/api/emergency/${responseId}`, payload);
  return data;
}

export async function getAlerts() {
  try {
    const { data } = await apiClient.get('/api/alerts', { params: { limit: 500 } });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/alerts:', error);
    return [];
  }
}

export async function createAlert(payload) {
  const { data } = await apiClient.post('/api/alerts', payload);
  return data;
}

export async function getAdminUsers() {
  try {
    const { data } = await apiClient.get('/api/admin/users');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/admin/users:', error);
    return [];
  }
}

export async function getAdminRoles() {
  try {
    const { data } = await apiClient.get('/api/admin/roles');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/admin/roles:', error);
    return [];
  }
}

export async function updateUserRole(username, roleId) {
  const { data } = await apiClient.patch(`/api/admin/users/${encodeURIComponent(username)}/role`, {
    role_id: roleId,
  });
  return data;
}

/**
 * Update a user's username (and optionally name/phone).
 * PATCH /api/admin/users/{user_id}/profile  (Super Admin only)
 * Body matches UserProfileUpdate (backend/app/schemas/auth.py):
 *   { username?, name?, phone? }  — username: 3-50 chars, letters/numbers/_ . -
 * Keyed by the stable user_id (not the display name), so it is safe to rename.
 */
export async function updateUserProfile(userId, payload) {
  const { data } = await apiClient.patch(
    `/api/admin/users/${encodeURIComponent(userId)}/profile`,
    payload
  );
  return data;
}

export async function updateUserStatus(username, isActive) {
  const { data } = await apiClient.patch(`/api/admin/users/${encodeURIComponent(username)}/status`, {
    is_active: isActive,
  });
  return data;
}

export async function deleteUser(username) {
  const { data } = await apiClient.delete(`/api/admin/users/${encodeURIComponent(username)}`);
  return data;
}

// -----------------------------------------------------------------------------
// 8. ROAD MANAGEMENT (full CRUD against /api/roads)
// -----------------------------------------------------------------------------

export async function getAllRoads(search = '') {
  try {
    const { data } = await apiClient.get('/api/roads', { params: search ? { search } : {} });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/roads:', error);
    return [];
  }
}

export async function createRoad(payload) {
  const { data } = await apiClient.post('/api/roads', payload);
  return data;
}

export async function updateRoad(roadId, payload) {
  const { data } = await apiClient.put(`/api/roads/${roadId}`, payload);
  return data;
}

export async function deleteRoad(roadId) {
  const { data } = await apiClient.delete(`/api/roads/${roadId}`);
  return data;
}

// -----------------------------------------------------------------------------
// 9. TRAFFIC MANAGEMENT (traffic records against /api/traffic)
// -----------------------------------------------------------------------------

export async function getTrafficRecords() {
  try {
    const { data } = await apiClient.get('/api/traffic');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/traffic:', error);
    return [];
  }
}

/**
 * Server-side paginated traffic records.
 * The backend applies filters + OFFSET/LIMIT and reports the overall match
 * count in the X-Total-Count header.
 * Returns { items, total }.
 */
export async function getTrafficRecordsPage({ page = 1, pageSize = 20, level = 'ALL', search = '' } = {}) {
  const { data, headers } = await apiClient.get('/api/traffic', {
    params: {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      congestion_level: level && level !== 'ALL' ? level : undefined,
      search: search || undefined,
    },
  });
  const items = Array.isArray(data) ? data : [];
  const headerTotal = Number(headers?.['x-total-count']);
  return { items, total: Number.isFinite(headerTotal) ? headerTotal : items.length };
}

export async function createTrafficRecord(payload) {
  const { data } = await apiClient.post('/api/traffic', payload);
  return data;
}

// -----------------------------------------------------------------------------
// 10. ALERTS — update/resolve (create/list already above)
// -----------------------------------------------------------------------------

export async function updateAlert(alertId, payload) {
  const { data } = await apiClient.patch(`/api/alerts/${alertId}`, payload);
  return data;
}

// -----------------------------------------------------------------------------
// 11. ACCIDENT HOTSPOTS (real DB-backed list — see backend/app/routers/accident_hotspots.py)
// -----------------------------------------------------------------------------

export async function getHotspots(limit = 20) {
  try {
    const { data } = await apiClient.get('/api/hotspots', { params: { limit } });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/hotspots:', error);
    return [];
  }
}

// -----------------------------------------------------------------------------
// 12. LIVE GEOCODING & ROUTING (OpenStreetMap Nominatim + OSRM — real 3rd-party
//     APIs, not mocked; see backend/app/routers/geocoding.py)
// -----------------------------------------------------------------------------

/**
 * Live place-name search. Hits OpenStreetMap Nominatim on the backend.
 * Returns [] on failure/no matches rather than throwing, since this backs
 * a type-ahead UI that should degrade gracefully.
 */
export async function geocodeSearch(query, city = 'Hyderabad', limit = 5) {
  if (!query || query.trim().length < 2) return [];
  try {
    const { data } = await apiClient.get('/api/geo/search', {
      params: { query: query.trim(), city, limit },
    });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching /api/geo/search:', error);
    return [];
  }
}

/**
 * Real street-level driving route between two points, via OSRM
 * (Open Source Routing Machine — a live public routing API, not a
 * straight line). Throws on failure so the caller can show a real error
 * instead of silently drawing nothing.
 */
export async function getDrivingRoute(startLat, startLng, endLat, endLng) {
  const { data } = await apiClient.get('/api/geo/route', {
    params: {
      start_lat: startLat,
      start_lng: startLng,
      end_lat: endLat,
      end_lng: endLng,
    },
  });
  return data;
}

/**
 * Reverse geocode: turn GPS coordinates (e.g. from the browser's location
 * API) into a human-readable label. Used by "Use my current location".
 */
export async function reverseGeocode(lat, lng) {
  const { data } = await apiClient.get('/api/geo/reverse', { params: { lat, lng } });
  return data;
}

// -----------------------------------------------------------------------------
// 13. VOICE ASSISTANT (spaCy location NER + regex fallback —
//     see backend/app/routers/voice.py, schemas/voice.py, services/voice_service.py)
// -----------------------------------------------------------------------------

/**
 * Health/status of the voice extraction service.
 * GET /api/voice/status -> { status, model_loaded, engine, labels }
 * Never throws: returns { status: 'offline', model_loaded: false } on failure
 * so the UI can show a calm "voice service offline" state.
 */
export async function getVoiceStatus() {
  try {
    const { data } = await apiClient.get('/api/voice/status', { timeout: 8000 });
    return data;
  } catch (error) {
    console.warn('Voice status check failed:', error.message);
    return { status: 'offline', model_loaded: false, engine: null, labels: [] };
  }
}

/**
 * Turn a spoken transcript into a start/end pair.
 * POST /api/voice/extract-route  { text }
 * Returns VoiceRouteExtractResponse:
 *   { success, start_location, end_location, raw_text, cleaned_text,
 *     method ('ner' | 'pattern' | 'hybrid' | 'partial' | 'none'),
 *     model_loaded, message }
 * success is true only when BOTH locations were found; for partial matches
 * the one that was found is still returned together with a helpful message.
 */
export async function extractRouteFromVoice(text) {
  const { data } = await apiClient.post('/api/voice/extract-route', { text });
  return data;
}

// -----------------------------------------------------------------------------
// 14. REPORTS & ANALYTICS EXPORT (Super Admin + Traffic Authority)
// -----------------------------------------------------------------------------

/**
 * Fetch a report as JSON (for on-screen preview) from /api/reports.
 * reportType: 'summary' | 'accidents' | 'traffic' | 'hotspots' | 'predictions'
 */
// <input type="date"> yields "YYYY-MM-DD"; the API expects datetimes. Make the
// end date inclusive by pushing it to the end of that day.
function toStartDateTime(d) {
  return d ? `${d}T00:00:00` : undefined;
}
function toEndDateTime(d) {
  return d ? `${d}T23:59:59` : undefined;
}

export async function getReportPreview(reportType, { startDate, endDate, limit = 200 } = {}) {
  const { data } = await apiClient.get('/api/reports', {
    params: {
      report_type: reportType,
      format: 'json',
      start_date: toStartDateTime(startDate),
      end_date: toEndDateTime(endDate),
      limit,
    },
  });
  return data;
}

/**
 * Server-side paginated report preview.
 * Returns { items, total, page, page_size, total_pages } for accidents /
 * traffic / hotspots / predictions. (The 'summary' report is a fixed KPI
 * list and is not paginated — use getReportPreview for it.)
 */
export async function getReportPage(reportType, { startDate, endDate, page = 1, pageSize = 20 } = {}) {
  const { data } = await apiClient.get('/api/reports', {
    params: {
      report_type: reportType,
      format: 'json',
      start_date: toStartDateTime(startDate),
      end_date: toEndDateTime(endDate),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

/**
 * Download a report as a CSV file from /api/reports and trigger a browser
 * save-as. Returns nothing — the side effect is the download itself.
 */
export async function downloadReportCsv(reportType, { startDate, endDate, limit = 1000 } = {}) {
  const response = await apiClient.get('/api/reports', {
    params: {
      report_type: reportType,
      format: 'csv',
      start_date: toStartDateTime(startDate),
      end_date: toEndDateTime(endDate),
      limit,
    },
    responseType: 'blob',
  });

  const disposition = response.headers['content-disposition'] || '';
  const match = disposition.match(/filename=([^;]+)/);
  const filename = match ? match[1].trim() : `roadsense_${reportType}_report.csv`;

  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default {
  API_BASE_URL,
  apiClient,
  getDashboardStats,
  getDashboardTrend,
  getRoads,
  getTrafficRecordsPage,
  getReportPreview,
  getReportPage,
  downloadReportCsv,
  getAnomalies,
  predictAnomaly,
  getTrafficLayer,
  getAccidentLayer,
  getHotspotsLayer,
  loginUser,
  registerUser,
  requestEmailVerification,
  verifyEmailUser,
  forgotPassword,
  resetPassword,
  logoutUser,
  sendChatbotMessage,
  predictRouteTraffic,
  predictRouteAccident,
  predictTraffic,
  getLatestTrafficPredictions,
  getLatestAccidentPredictions,
  getZones,
  getAccidents,
  createAccident,
  getEmergencyResponses,
  createEmergencyResponse,
  getAlerts,
  createAlert,
  getAdminUsers,
  getAdminRoles,
  updateUserRole,
  updateUserStatus,
  updateUserProfile,
  deleteUser,
  getVoiceStatus,
  extractRouteFromVoice,
  updateMyProfile,
};
export async function getEmergencyResponders() {
  try {
    const { data } = await apiClient.get("/api/emergency/responders");
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error("Error fetching emergency responders:", error);
    throw error;
  }
}