import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

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
      {/* Public Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Authentication & Onboarding */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* Everything below requires a logged-in user */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/live-map" element={<LiveMap />} />
          <Route path="/traffic-prediction" element={<TrafficPrediction />} />
          <Route path="/Accident-Prediction" element={<AccidentPrediction />} />
          <Route path="/hotspots" element={<HotspotsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          
          {/* Super Admin + Traffic Authority only */}
          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY]} />}>
            <Route path="/traffic-management" element={<TrafficManagement />} />
            <Route path="/road-management" element={<RoadManagement />} />
          </Route>

          {/* Super Admin only */}
          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN]} />}>
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/anomalies" element={<AnomaliesPage />} />

          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}