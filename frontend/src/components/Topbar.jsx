import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { ROLE_LABELS } from '../utils/constants';

export default function Topbar({ title }) {
  const { user, logout } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();

  async function handleLogout() {
    navigate('/', { replace: true });
    await logout();
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 dark:border-asphalt-700 dark:bg-asphalt-900">
      <h1 className="text-base font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">{title}</h1>

      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
          className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-500 transition-colors hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
        >
          {isDarkMode ? '☀️' : '🌙'}
        </button>

        <div className="text-right">
          <p className="text-sm leading-tight text-slate-900 dark:text-asphalt-100">{user?.name}</p>
          <p className="text-xs leading-tight text-slate-500 dark:text-asphalt-400">
            {ROLE_LABELS[user?.role] || user?.role}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-500 transition-colors hover:border-signal-red/50 hover:text-signal-red dark:border-asphalt-600 dark:text-asphalt-300"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
