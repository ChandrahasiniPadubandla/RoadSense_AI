import React from 'react';
import { Link } from 'react-router-dom';
import { Bell, Menu } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { ROLE_LABELS } from '../utils/constants';
import { NAV_ITEMS } from './Sidebar';

const ALERT_ROLES = NAV_ITEMS.find((i) => i.to === '/alerts')?.roles || [];

export default function Topbar({ title, onMenuClick }) {
  const { user } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const canSeeAlerts = ALERT_ROLES.includes(user?.role);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 dark:border-asphalt-700 dark:bg-asphalt-900">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          title="Open menu"
          aria-label="Open menu"
          className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-500 transition-colors hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
        >
          <Menu size={16} />
        </button>
        <h1 className="text-base font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">{title}</h1>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
          className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-500 transition-colors hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
        >
          {isDarkMode ? '☀️' : '🌙'}
        </button>
        {canSeeAlerts && (
          <Link
            to="/alerts"
            title="Alerts"
            aria-label="Alerts"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-500 transition-colors hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
          >
            <Bell size={16} />
          </Link>
        )}

        <div className="text-right">
          <p className="text-sm leading-tight text-slate-900 dark:text-asphalt-100">{user?.name}</p>
          <p className="text-xs leading-tight text-slate-500 dark:text-asphalt-400">
            {ROLE_LABELS[user?.role] || user?.role}
          </p>
        </div>

        
      </div>
    </header>
  );
}
