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
import ReportsPage from './pages/ReportsPage';
import IncidentsPage from './pages/IncidentsPage';
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

          {/* Super Admin → sees everything */}
          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN]} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/live-map" element={<LiveMap />} />
            <Route path="/traffic-prediction" element={<TrafficPrediction />} />
            <Route path="/accident-prediction" element={<AccidentPrediction />} />
            <Route path="/hotspots" element={<HotspotsPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/traffic-management" element={<TrafficManagement />} />
            <Route path="/road-management" element={<RoadManagement />} />
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/anomalies" element={<AnomaliesPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Route>

          {/* Super Admin + Traffic Authority + Emergency Response */}
          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE]} />}>
            <Route path="/incidents" element={<IncidentsPage />} />
          </Route>

          {/* Traffic Authority only */}
          <Route element={<RoleRoute allow={[ROLES.TRAFFIC_AUTHORITY]} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/traffic-management" element={<TrafficManagement />} />
            <Route path="/road-management" element={<RoadManagement />} />
            <Route path="/alerts" element={<AlertsPage />} />
          </Route>

          {/* Emergency Response only */}
          <Route element={<RoleRoute allow={[ROLES.EMERGENCY_RESPONSE]} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/hotspots" element={<HotspotsPage />} />
            <Route path="/accident-prediction" element={<AccidentPrediction />} />
          </Route>

          {/* Normal User only */}
          <Route element={<RoleRoute allow={[ROLES.USER]} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/live-map" element={<LiveMap />} />
            <Route path="/traffic-prediction" element={<TrafficPrediction />} />
            <Route path="/accident-prediction" element={<AccidentPrediction />} />
          </Route>

        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
