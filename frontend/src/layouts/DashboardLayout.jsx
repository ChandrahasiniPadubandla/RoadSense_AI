import React, { useCallback, useState } from 'react';
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

  const title =
    TITLES[pathname] ||
    TITLES[pathname.toLowerCase()] ||
    'Smart Traffic System';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-asphalt-950">

      {/* =========================================================
          LEFT NAVIGATION SIDEBAR
      ========================================================= */}

      <Sidebar
        open={sidebarOpen}
        onClose={closeSidebar}
      />

      {/* =========================================================
          MAIN APPLICATION AREA
          - Moves right when navigation sidebar opens
          - Shrinks from right when chatbot opens
      ========================================================= */}

      <div
        className={`
          min-h-screen
          transition-all
          duration-300
          ease-in-out

          ${sidebarOpen ? 'ml-64' : 'ml-0'}

          ${chatOpen ? 'mr-[360px]' : 'mr-0'}
        `}
      >

        {/* TOPBAR */}

        <Topbar
          title={title}
          onMenuClick={() => setSidebarOpen((v) => !v)}
        />

        {/* PAGE CONTENT */}

        <main className="min-h-[calc(100vh-64px)] overflow-y-auto p-6">
          <Outlet />
        </main>

      </div>

      {/* =========================================================
          AI CHAT
      ========================================================= */}

      <ChatWidget
        isOpen={chatOpen}
        setIsOpen={setChatOpen}
      />

    </div>
  );
}