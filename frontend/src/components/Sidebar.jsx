import React, { useEffect, useRef } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ROLES } from '../utils/constants';

export const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE, ROLES.VIEWER] },
  { to: '/live-map', label: 'Live Map', roles: [ROLES.SUPER_ADMIN, ROLES.VIEWER, ROLES.EMERGENCY_RESPONSE, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/traffic-prediction', label: 'Traffic Prediction', roles: [ROLES.SUPER_ADMIN, ROLES.VIEWER] },
  { to: '/accident-prediction', label: 'Accident Prediction', roles: [ROLES.SUPER_ADMIN, ROLES.EMERGENCY_RESPONSE, ROLES.VIEWER] },
  { to: '/traffic-management', label: 'Traffic Management', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/hotspots', label: 'Accident Hotspots', roles: [ROLES.SUPER_ADMIN, ROLES.EMERGENCY_RESPONSE, ROLES.VIEWER] },
  { to: '/anomalies', label: 'Anomalies', roles: [ROLES.SUPER_ADMIN] },
  { to: '/alerts', label: 'Alerts', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.VIEWER] },
  { to: '/incidents', label: 'Incidents', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE] },
  { to: '/road-management', label: 'Road Management', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/reports', label: 'Reports', roles: [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY] },
  { to: '/user-management', label: 'User Management', roles: [ROLES.SUPER_ADMIN] },
];

/**
 * Slide-in sidebar. Opened/closed via Topbar hamburger button, backdrop click,
 * Escape key, or page navigation.
 */
export default function Sidebar({ open = false, onClose = () => {} }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  // Normalize role and fallback to VIEWER so the sidebar never vanishes if role is hydrating
  const userRole = (user?.role || ROLES.VIEWER).toUpperCase();
  const visibleItems = NAV_ITEMS.filter((item) =>
    item.roles.includes(userRole)
  );

  // Close after navigating to another page
  useEffect(() => {
    if (open && typeof onClose === 'function') {
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape' && typeof onClose === 'function') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  async function handleLogout() {
    if (typeof onClose === 'function') onClose();
    navigate('/', { replace: true });
    await logout();
  }

  return (
    <>
      {/* Backdrop */}
      <div
  onClick={onClose}
  aria-hidden
  className={`
    fixed
    inset-0
    z-[1999]

    bg-slate-900/30
    backdrop-blur-[1px]

    transition-opacity
    duration-200

    md:hidden

    ${
      open
        ? 'opacity-100 pointer-events-auto'
        : 'pointer-events-none opacity-0'
    }
  `}
/>

      <aside
        aria-hidden={!open}
        className={`fixed inset-y-0 left-0 z-[2000] flex w-64 flex-col border-r border-slate-200 bg-white shadow-2xl transition-transform duration-200 ease-out dark:border-asphalt-700 dark:bg-asphalt-900 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="border-b border-slate-200 px-5 py-5 dark:border-asphalt-700">
          <p className="text-sm font-black tracking-tight text-slate-900 dark:text-asphalt-100">
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
              tabIndex={open ? 0 : -1}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-signal-blue/15 text-signal-blue font-semibold'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-asphalt-300 dark:hover:bg-asphalt-800 dark:hover:text-asphalt-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Logout pinned to the bottom */}
        <div className="border-t border-slate-200 p-3 dark:border-asphalt-700">
          <button
            onClick={handleLogout}
            tabIndex={open ? 0 : -1}
            className="flex w-full items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 transition-colors hover:border-signal-red/50 hover:text-signal-red dark:border-asphalt-600 dark:text-asphalt-300"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>
    </>
  );
}
