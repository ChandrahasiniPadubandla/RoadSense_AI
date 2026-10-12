import React, { useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { SEVERITY_COLOR, ROLES } from '../utils/constants';
import { useAuth } from '../context/AuthContext';
import { getAlerts, updateAlert } from '../api_services';

const STATUS_OPTIONS = ['ALL', 'ACTIVE', 'RESOLVED'];

export default function AlertsPage() {
  const { user } = useAuth();
  const canResolve = [ROLES.SUPER_ADMIN, ROLES.TRAFFIC_AUTHORITY, ROLES.EMERGENCY_RESPONSE].includes(user?.role);

  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ACTIVE');
  const [busyId, setBusyId] = useState(null);
  const [actionError, setActionError] = useState('');

  async function load() {
    setIsLoading(true);
    try {
      const data = await getAlerts();
      setAlerts(data);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    if (statusFilter === 'ALL') return alerts;
    return alerts.filter((a) => (a.status || '').toUpperCase() === statusFilter);
  }, [alerts, statusFilter]);

  async function handleResolve(alert) {
    setBusyId(alert.alert_id);
    setActionError('');
    try {
      await updateAlert(alert.alert_id, { status: 'RESOLVED', resolved_at: new Date().toISOString() });
      await load();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to update alert.');
    } finally {
      setBusyId(null);
    }
  }

  const inputClass =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-asphalt-100">Alerts</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Real alerts raised by the system — accident, congestion, road, and emergency notifications from the database.
        </p>
      </div>

      <div className="flex gap-2">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === s
                ? 'border-signal-blue bg-signal-blue/10 text-signal-blue'
                : 'border-slate-300 text-slate-500 hover:border-signal-blue/40 dark:border-asphalt-600 dark:text-asphalt-300'
            }`}
          >
            {s === 'ALL' ? 'All' : s.charAt(0) + s.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      {actionError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {actionError}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading alerts…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'alert_type', header: 'Type', render: (a) => a.alert_type || 'ALERT' },
            {
              key: 'severity',
              header: 'Severity',
              render: (a) => <LevelBadge level={(a.severity || 'UNKNOWN').toUpperCase()} colorMap={SEVERITY_COLOR} />,
            },
            { key: 'message', header: 'Message', render: (a) => a.message || '—' },
            {
              key: 'created_at',
              header: 'Raised',
              render: (a) => (a.created_at ? new Date(a.created_at).toLocaleString() : '—'),
            },
            {
              key: 'status',
              header: 'Status',
              render: (a) => (
                <span className={a.status === 'ACTIVE' ? 'text-signal-red' : 'text-signal-green'}>{a.status}</span>
              ),
            },
            ...(canResolve
              ? [
                  {
                    key: 'actions',
                    header: 'Actions',
                    render: (a) =>
                      a.status === 'ACTIVE' ? (
                        <button
                          onClick={() => handleResolve(a)}
                          disabled={busyId === a.alert_id}
                          className="text-signal-blue hover:underline disabled:opacity-50"
                        >
                          {busyId === a.alert_id ? 'Resolving…' : 'Mark resolved'}
                        </button>
                      ) : (
                        <span className="text-slate-400 dark:text-asphalt-500">—</span>
                      ),
                  },
                ]
              : []),
          ]}
          rows={filtered.map((a) => ({ ...a, id: a.alert_id }))}
          emptyMessage="No alerts found for this filter."
        />
      )}
    </div>
  );
}
