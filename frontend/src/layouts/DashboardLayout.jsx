import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Topbar from '../components/Topbar';
import ChatWidget from '../components/ChatWidget';

const TITLES = {
  '/': 'Dashboard',
  '/overview': 'Traffic & Risk Overview',
  '/live-map': 'Live Traffic Map',
  '/traffic': 'Traffic Monitoring',
  '/predictions': 'Congestion Prediction',
  '/anomalies': 'Anomaly Detection',
  '/accidents': 'Accident Management',
  '/accident-risk': 'Accident Risk Prediction',
  '/hotspots': 'Accident Hotspots',
  '/emergency-responses': 'Emergency Response',
  '/alerts': 'Alerts',
  '/users': 'User Management',
};

export default function DashboardLayout() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] || 'Smart Traffic System';

  return (
    <div className="flex h-screen bg-asphalt-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
      <ChatWidget />
    </div>
  );
}
