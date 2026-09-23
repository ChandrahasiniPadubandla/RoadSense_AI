import React, { useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { SEVERITY_COLOR } from '../utils/constants';
import { getEmergencyResponses, updateEmergencyResponse } from '../api_services';

const STATUS_OPTIONS = ['PENDING', 'EN_ROUTE', 'ARRIVED', 'RESOLVED'];

const STATUS_COLOR = {
  PENDING: 'text-signal-amber border-signal-amber/40 bg-signal-amber/10',
  EN_ROUTE: 'text-signal-blue border-signal-blue/40 bg-signal-blue/10',
  ARRIVED: 'text-signal-blue border-signal-blue/40 bg-signal-blue/10',
  RESOLVED: 'text-signal-green border-signal-green/40 bg-signal-green/10',
};

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [busyId, setBusyId] = useState(null);
  const [actionError, setActionError] = useState('');
  const [loadError, setLoadError] = useState('');

  async function load() {
    setIsLoading(true);
    setLoadError('');
    try {
      const params = statusFilter === 'ALL' ? {} : { response_status: statusFilter };
      const data = await getEmergencyResponses(params);
      setIncidents(data);
    } catch (err) {
      setIncidents([]);
      const status = err.response?.status;
      if (status === 401 || status === 403) {
        setLoadError('Your session is invalid or you do not have permission to view incidents. Please log in again.');
      } else {
        setLoadError(err.response?.data?.detail || 'Unable to load incidents from the server. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
   
  }, [statusFilter]);

  async function handleStatusChange(incident, newStatus) {
    setBusyId(incident.response_id);
    setActionError('');
    try {
      await updateEmergencyResponse(incident.response_id, { response_status: newStatus });
      await load();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to update incident status.');
    } finally {
      setBusyId(null);
    }
  }

  const inputClass =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Emergency Response"
        title="Incidents"
        subtitle="Real accident incidents assigned for emergency response, with live severity and status tracking."
      />

      <div className="flex flex-wrap gap-2">
        {['ALL', ...STATUS_OPTIONS].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === s
                ? 'border-signal-blue bg-signal-blue/10 text-signal-blue'
                : 'border-slate-300 text-slate-500 hover:border-signal-blue/40 dark:border-asphalt-600 dark:text-asphalt-300'
            }`}
          >
            {s === 'ALL' ? 'All' : s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {actionError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">{actionError}</div>
      )}

      {loadError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {loadError}
          <button
            type="button"
            onClick={load}
            className="ml-2 font-medium underline underline-offset-2 hover:opacity-80"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading incidents…</p>
      ) : loadError ? null : (
        <DataTable
          columns={[
            {
              key: 'road',
              header: 'Location',
              render: (i) => i.accident?.road_name || 'Unknown road',
            },
            {
              key: 'severity',
              header: 'Severity',
              render: (i) =>
                i.accident?.severity ? (
                  <LevelBadge level={i.accident.severity.toUpperCase()} colorMap={SEVERITY_COLOR} />
                ) : (
                  '—'
                ),
            },
            {
              key: 'accident_datetime',
              header: 'Occurred',
              render: (i) => (i.accident?.accident_datetime ? new Date(i.accident.accident_datetime).toLocaleString() : '—'),
            },
            {
              key: 'casualties',
              header: 'Casualties',
              render: (i) =>
                i.accident ? `${i.accident.fatalities} fatal · ${i.accident.injuries} injured` : '—',
            },
            {
              key: 'response_status',
              header: 'Status',
              render: (i) => (
                <select
                  value={i.response_status || 'PENDING'}
                  disabled={busyId === i.response_id}
                  onChange={(e) => handleStatusChange(i, e.target.value)}
                  className={`rounded-full border px-2 py-1 text-xs font-medium outline-none ${STATUS_COLOR[i.response_status] || STATUS_COLOR.PENDING}`}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              ),
            },
            {
              key: 'resolved_at',
              header: 'Resolved',
              render: (i) => (i.resolved_at ? new Date(i.resolved_at).toLocaleString() : '—'),
            },
          ]}
          rows={incidents.map((i) => ({ ...i, id: i.response_id }))}
          emptyMessage="No emergency responses recorded for this filter."
        />
      )}
    </div>
  );
}
