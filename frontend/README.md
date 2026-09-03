# Smart Traffic & Accident Prediction System — Frontend

React (Vite) + Tailwind + React Router + Axios + Recharts + Leaflet.
Runs fully on **mock data** right now, so every screen works before the backend exists.

---

## 1. Get it running in VS Code (do this first)

```bash
# 1. Open the smart-traffic-dashboard folder in VS Code
# 2. Open a terminal (Ctrl+`) and run:
npm install
cp .env.example .env
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`). Log in with any demo account
shown on the login screen (e.g. `admin@traffic.gov` / `admin123`).

If `npm install` fails, make sure Node.js 18+ is installed (`node -v`).

---

## 2. Project structure

```
src/
  api/            <- ALL backend calls live here. Nothing else calls axios directly.
    axiosClient.js      base URL, auth header, 401 handling
    authService.js      login/logout
    trafficService.js   roads, congestion prediction, anomalies, dashboard stats
    accidentService.js  accident CRUD, hotspots, risk prediction
    alertService.js     alerts + acknowledge
  context/
    AuthContext.jsx      logged-in user, role, token, login()/logout()
  routes/
    ProtectedRoute.jsx   redirects to /login if not authenticated
    RoleRoute.jsx         redirects to /unauthorized if role not allowed
  layouts/
    DashboardLayout.jsx   sidebar + topbar + page content
  components/              Sidebar, Topbar, StatCard, LevelBadge, DataTable
  pages/                   one file per screen (Dashboard, LiveMap, TrafficMonitoring, ...)
  mock/
    mockData.js           fake data — also documents the exact shape the API should return
  utils/constants.js       roles, colors for traffic/risk/severity levels
```

---

## 3. Suggested 10-day build order

You already have all the code — this order is how to **learn it and extend it**
day by day rather than being handed a black box. Re-read each area's files as you go.

| Day | Focus | Files to study/extend |
|---|---|---|
| 1 | Project setup, run it, understand routing | `App.jsx`, `main.jsx`, folder structure |
| 2 | Auth flow: login, JWT storage, session restore | `context/AuthContext.jsx`, `api/authService.js`, `pages/Login.jsx` |
| 3 | Route guards & role-based sidebar | `routes/ProtectedRoute.jsx`, `routes/RoleRoute.jsx`, `components/Sidebar.jsx` |
| 4 | Dashboard shell + stats + chart | `pages/Dashboard.jsx`, `components/StatCard.jsx` |
| 5 | Traffic monitoring module (module 2) | `pages/TrafficMonitoring.jsx`, `api/trafficService.js` |
| 6 | Congestion prediction + anomaly detection (modules 3, 7) | `pages/TrafficPrediction.jsx`, `pages/AnomalyDetection.jsx` |
| 7 | Accident management (module 4) — list + create form | `pages/AccidentManagement.jsx`, `api/accidentService.js` |
| 8 | Accident risk prediction + hotspots (modules 5, 6) | `pages/AccidentRiskPrediction.jsx`, `pages/AccidentHotspots.jsx` |
| 9 | Live map with Leaflet (module 9) | `pages/LiveMap.jsx` |
| 10 | Alerts (module 10), user management, polish, connect real backend | `pages/Alerts.jsx`, `pages/UserManagement.jsx`, see section 5 below |

Each page is self-contained, so you can genuinely build/test them in this order without
breaking earlier days.

---

## 4. Roles implemented

| Role | Access |
|---|---|
| `SUPER_ADMIN` | everything, including User Management |
| `TRAFFIC_AUTHORITY` | traffic monitoring, predictions, anomalies, accident management, risk prediction |
| `EMERGENCY_RESPONSE` | traffic monitoring, accident management, hotspots, alerts |
| `VIEWER` | dashboard, live map, traffic monitoring, hotspots, alerts (read-only) |

Change what each role can see in `src/components/Sidebar.jsx` (nav items) and
`src/App.jsx` (`<RoleRoute allow={[...]}>` wrappers).

---

## 5. Connecting the real backend (do this once it's ready)

This is the part of your original question — **what changes when the backend is live**.
The app was built specifically to make this a small, mechanical change:

### Step 1 — Flip the mock flag
In `.env`:
```
VITE_API_BASE_URL=https://your-real-api.com/api
VITE_USE_MOCK_DATA=false
```
Restart `npm run dev` after editing `.env` (Vite only reads it on startup).

### Step 2 — Confirm your backend matches these endpoints
Every function in `src/api/*.js` has a comment showing the exact endpoint and
response shape it expects. Summary:

| Function | Method & path | Notes |
|---|---|---|
| `login` | `POST /auth/login` | body `{email,password}` → `{accessToken, user}` |
| `getRoads` | `GET /traffic/roads` | array of road objects |
| `getRoadById` | `GET /traffic/roads/:id` | |
| `getCongestionPredictions` | `GET /traffic/predictions` | |
| `getAnomalies` | `GET /traffic/anomalies` | |
| `getDashboardStats` | `GET /dashboard/stats` | `{activeRoads, highTraffic, accidentAlerts, highRiskZones}` |
| `getTrafficHistory` | `GET /traffic/history?roadId=` | |
| `getAccidents` | `GET /accidents` | |
| `createAccident` | `POST /accidents` | |
| `getHotspots` | `GET /accidents/hotspots` | |
| `getRiskPredictions` | `GET /accidents/risk-predictions` | |
| `getAlerts` | `GET /alerts` | |
| `acknowledgeAlert` | `PATCH /alerts/:id/acknowledge` | |

If your backend uses different field names or routes, **you only need to edit the
matching function in `src/api/*.js`** — no page component needs to change, because
pages only ever call these service functions, never axios directly.

### Step 3 — Field name mismatches
If the backend's JSON keys differ from the mock shape (e.g. `vehicle_count` instead
of `vehicleCount`), either:
- adjust the backend response, or
- map it inside the relevant service function, e.g.:
  ```js
  const { data } = await axiosClient.get('/traffic/roads');
  return data.map((r) => ({ ...r, vehicleCount: r.vehicle_count }));
  ```

### Step 4 — Auth token handling
`axiosClient.js` already attaches `Authorization: Bearer <token>` from
`localStorage` on every request, and redirects to `/login` on a 401. If your backend
issues a refresh token instead of a long-lived access token, add refresh logic in the
response interceptor there — that's the only file that needs it.

### Step 5 — CORS
If you get CORS errors in the browser console, your backend needs to allow
`http://localhost:5173` (or your deployed frontend URL) as an allowed origin. This is
a backend-side config, not something to fix in React.

### Step 6 — Remove mock-only UI
`pages/Login.jsx` shows a "demo accounts" box — delete that block once real accounts exist.
`pages/UserManagement.jsx` currently reads from `mock/mockData.js` directly (not through
a service file, since there's no `userService.js` yet) — create one following the same
pattern as `accidentService.js` and swap it in.

### Nothing else changes
Routing, role guards, layout, charts, the map, and every page's UI logic are already
backend-agnostic — they only depend on the shape of data coming back from `api/*.js`.

---

## 6. Notes

- Map tiles come from the public OpenStreetMap tile server — fine for development;
  check their usage policy before high-traffic production use, or switch the `url` in
  `LiveMap.jsx` to a provider like MapTiler/Mapbox.
- `recharts` is used for the dashboard trend chart; swap in more charts the same way
  for any other module (e.g. per-road historical trends).
- Colors and level styling (traffic level, risk level, severity) are centralized in
  `src/utils/constants.js` — change the whole app's color coding from one file.
