import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import ProtectedRoute from './routes/ProtectedRoute';
import DashboardLayout from './layouts/DashboardLayout';

import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import Dashboard from './pages/Dashboard';
import LiveMap from './pages/LiveMap';
import TrafficPrediction from './pages/TrafficPrediction';
import AccidentPrediction from './pages/AccidentPrediction';      
import Unauthorized from './pages/Unauthorized';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* Everything below requires a logged-in user */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live-map" element={<LiveMap />} />
          <Route path="/map" element={<Navigate to="/live-map" replace />} />
          <Route path="/traffic-prediction" element={<TrafficPrediction />} />
          <Route path="/Accident-Prediction" element={<AccidentPrediction />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
