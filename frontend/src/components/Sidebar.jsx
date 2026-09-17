import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLES } from '../utils/constants';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', roles: 'ALL' },
  { to: '/live-map', label: 'Map', roles: 'ALL' },
  { to: '/traffic-prediction', label: 'Traffic Prediction', roles: 'ALL' },
  { to: '/Accident-Prediction', label: 'Accident Prediction', roles: 'ALL' },
  { to: '/traffic-management', label: 'Traffic Management', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/hotspots', label: 'Accident Hotspots', roles: 'ALL' },
  { to: '/alerts', label: 'Alerts', roles: 'ALL' },
  { to: '/road-management', label: 'Road Management', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/user-management', label: 'User Management', roles: [ROLES.SUPER_ADMIN] },
];

export default function Sidebar() {
  const { user } = useAuth();

  const visibleItems = NAV_ITEMS.filter(
    (item) => item.roles === 'ALL' || item.roles.includes(user?.role)
  );

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-asphalt-700 dark:bg-asphalt-900 md:flex">
      <div className="border-b border-slate-200 px-5 py-5 dark:border-asphalt-700">
        <p className="text-sm font-semibold tracking-tight text-slate-900 dark:text-asphalt-100">
          Smart Traffic System
        </p>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-asphalt-400">
          Prediction &amp; Monitoring
        </p>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/dashboard'}
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-signal-blue/15 text-signal-blue'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-asphalt-300 dark:hover:bg-asphalt-800 dark:hover:text-asphalt-100'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
