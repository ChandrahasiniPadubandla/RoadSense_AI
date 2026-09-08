import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLES } from '../utils/constants';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', roles: 'ALL' },
  { to: '/overview', label: 'Traffic & Risk Overview', roles: 'ALL' },
  { to: '/live-map', label: 'Live Map', roles: 'ALL' },
  { to: '/traffic', label: 'Traffic Monitoring', roles: 'ALL' },
  { to: '/predictions', label: 'Congestion Prediction', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/anomalies', label: 'Anomaly Detection', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/accidents', label: 'Accident Management', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE] },
  { to: '/accident-risk', label: 'Accident Risk Prediction', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/hotspots', label: 'Accident Hotspots', roles: 'ALL' },
  { to: '/emergency-responses', label: 'Emergency Response', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE] },
  { to: '/alerts', label: 'Alerts', roles: 'ALL' },
  { to: '/users', label: 'User Management', roles: [ROLES.SUPER_ADMIN] },
];

export default function Sidebar() {
  const { user } = useAuth();

  const visibleItems = NAV_ITEMS.filter(
    (item) => item.roles === 'ALL' || item.roles.includes(user?.role)
  );

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-asphalt-700 bg-asphalt-900 md:flex">
      <div className="border-b border-asphalt-700 px-5 py-5">
        <p className="text-sm font-semibold tracking-tight text-asphalt-100">
          Smart Traffic System
        </p>
        <p className="mt-0.5 text-xs text-asphalt-400">
          Prediction &amp; Monitoring
        </p>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-signal-blue/15 text-signal-blue'
                  : 'text-asphalt-300 hover:bg-asphalt-800 hover:text-asphalt-100'
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
