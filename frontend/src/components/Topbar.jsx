import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/constants';

export default function Topbar({ title }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-asphalt-700 bg-asphalt-900 px-6">
      <h1 className="text-sm font-medium text-asphalt-100">{title}</h1>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm leading-tight text-asphalt-100">{user?.name}</p>
          <p className="text-xs leading-tight text-asphalt-400">
            {ROLE_LABELS[user?.role] || user?.role}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="rounded-md border border-asphalt-600 px-3 py-1.5 text-xs text-asphalt-300 transition-colors hover:border-signal-red/50 hover:text-signal-red"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
