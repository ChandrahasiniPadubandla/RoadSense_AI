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
    'Metrivon ';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="h-screen overflow-hidden bg-slate-50 dark:bg-asphalt-950">

      {/* =========================================================
          LEFT NAVIGATION SIDEBAR
      ========================================================= */}

      <Sidebar
        open={sidebarOpen}
        onClose={closeSidebar}
      />

      {/* =========================================================
          MAIN APPLICATION AREA
      ========================================================= */}

      <div
        className={`
          h-screen
          transition-all
          duration-300
          ease-in-out
          flex
          flex-col

          ${sidebarOpen ? 'ml-64' : 'ml-0'}
          ${chatOpen ? 'mr-[360px]' : 'mr-0'}
        `}
      >

        {/* =======================================================
            TOPBAR
        ======================================================= */}

        <div className="shrink-0">
          <Topbar
            title={title}
            onMenuClick={() => setSidebarOpen((v) => !v)}
          />
        </div>

        {/* =======================================================
            SCROLLABLE PAGE AREA
        ======================================================= */}

        <main
          className="
            flex-1
            min-h-0
            overflow-y-auto
            overflow-x-hidden
            p-6
          "
        >
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