import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Topbar from '../components/Topbar';
import ChatWidget from '../components/ChatWidget';

const TITLES = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/live-map': 'Live Map',
  '/map': 'Live Map',
  '/traffic-prediction': 'Traffic Prediction',
  '/Accident-Prediction': 'Accident Prediction',
  '/traffic-management': 'Traffic Management',
  '/hotspots': 'Accident Hotspots',
  '/alerts': 'Alerts',
  '/anomalies': 'Traffic Anomalies',
  '/incidents': 'Incidents',
  '/road-management': 'Road Management',
  '/reports': 'Reports',
  '/user-management': 'User Management',
};

export default function DashboardLayout() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] || 'Smart Traffic System';

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-asphalt-950">
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
