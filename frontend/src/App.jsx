import React from 'react';
import { Routes, Route } from 'react-router-dom';

import ProtectedRoute from './routes/ProtectedRoute';
import RoleRoute from './routes/RoleRoute';
import DashboardLayout from './layouts/DashboardLayout';

import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import Dashboard from './pages/Dashboard';
import LiveMap from './pages/LiveMap';
import RoadOverview from './pages/RoadOverview';
import TrafficMonitoring from './pages/TrafficMonitoring';
import TrafficPrediction from './pages/TrafficPrediction';
import AnomalyDetection from './pages/AnomalyDetection';
import AccidentManagement from './pages/AccidentManagement';
import AccidentRiskPrediction from './pages/AccidentRiskPrediction';
import AccidentHotspots from './pages/AccidentHotspots';
import EmergencyResponse from './pages/EmergencyResponse';
import Alerts from './pages/Alerts';
import UserManagement from './pages/UserManagement';
import Unauthorized from './pages/Unauthorized';
import NotFound from './pages/NotFound';

import { ROLES } from './utils/constants';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* Everything below requires a logged-in user */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/overview" element={<RoadOverview />} />
          <Route path="/live-map" element={<LiveMap />} />
          <Route path="/traffic" element={<TrafficMonitoring />} />
          <Route path="/hotspots" element={<AccidentHotspots />} />
          <Route path="/alerts" element={<Alerts />} />

          <Route
            element={
              <RoleRoute allow={[ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY]} />
            }
          >
            <Route path="/predictions" element={<TrafficPrediction />} />
            <Route path="/anomalies" element={<AnomalyDetection />} />
            <Route path="/accident-risk" element={<AccidentRiskPrediction />} />
          </Route>

          <Route
            element={
              <RoleRoute
                allow={[
                  ROLES.SUPER_ADMIN,
                  ROLES.TRAFFIC_AUTHORITY,
                  ROLES.EMERGENCY_RESPONSE,
                ]}
              />
            }
          >
            <Route path="/accidents" element={<AccidentManagement />} />
            <Route path="/emergency-responses" element={<EmergencyResponse />} />
          </Route>

          <Route element={<RoleRoute allow={[ROLES.SUPER_ADMIN]} />}>
            <Route path="/users" element={<UserManagement />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
