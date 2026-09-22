import React from 'react';  
import { Routes, Route } from 'react-router-dom';

import ProtectedRoute from './routes/ProtectedRoute';
import RoleRoute from './routes/RoleRoute';
import DashboardLayout from './layouts/DashboardLayout';

import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import LiveMap from './pages/LiveMap';
import TrafficPrediction from './pages/TrafficPrediction';
import AccidentPrediction from './pages/AccidentPrediction';
import TrafficManagement from './pages/TrafficManagement';
import HotspotsPage from './pages/HotspotsPage';
import AlertsPage from './pages/AlertsPage';
import RoadManagement from './pages/RoadManagement';
import UserManagement from './pages/UserManagement';
import Unauthorized from './pages/Unauthorized';
import AnomaliesPage from './pages/AnomaliesPage';
import NotFound from './pages/NotFound';
import { ROLES } from './utils/constants';

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>

          <Route element={<RoleRoute allow={Object.values(ROLES)} />}>
            <Route path="/dashboard" element={<Dashboard />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.VIEWER]} />}>
            <Route path="/live-map" element={<LiveMap />} />
            <Route path="/traffic-prediction" element={<TrafficPrediction />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.EMERGENCY_RESPONSE, ROLES.VIEWER]} />}>
            <Route path="/accident-prediction" element={<AccidentPrediction />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.EMERGENCY_RESPONSE]} />}>
            <Route path="/hotspots" element={<HotspotsPage />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY]} />}>
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/traffic-management" element={<TrafficManagement />} />
            <Route path="/road-management" element={<RoadManagement />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN]} />}>
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/anomalies" element={<AnomaliesPage />} />
          </Route>

        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
