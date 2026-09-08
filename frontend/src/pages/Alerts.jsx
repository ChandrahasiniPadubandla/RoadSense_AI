import React, { useEffect, useState } from 'react';
import * as alertService from '../api/alertService';

const SEVERITY_STYLES = {
  HIGH: 'border-signal-red/40 bg-signal-red/10 text-signal-red',
  MEDIUM: 'border-signal-amber/40 bg-signal-amber/10 text-signal-amber',
  LOW: 'border-signal-green/40 bg-signal-green/10 text-signal-green',
};

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  function load() {
    return alertService.getAlerts().then((data) => {
      setAlerts(data);
      setIsLoading(false);
    });
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAcknowledge(id) {
    await alertService.acknowledgeAlert(id);
    load();
  }

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading alerts…</p>;

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`flex items-start justify-between rounded-lg border p-4 ${
            alert.acknowledged
              ? 'border-asphalt-700 bg-asphalt-900 opacity-60'
              : SEVERITY_STYLES[alert.severity] || 'border-asphalt-700 bg-asphalt-900'
          }`}
        >
          <div>
            <p className="text-xs font-medium uppercase tracking-wide">
              {alert.type.replace('_', ' ')} · {alert.severity}
            </p>
            <p className="mt-1 text-sm text-asphalt-100">{alert.message}</p>
            <p className="mt-1 text-xs text-asphalt-400">
              {alert.roadName} · {new Date(alert.createdAt).toLocaleTimeString()}
            </p>
          </div>
          {!alert.acknowledged && (
            <button
              onClick={() => handleAcknowledge(alert.id)}
              className="shrink-0 rounded-md border border-asphalt-600 px-3 py-1.5 text-xs text-asphalt-200 hover:border-signal-blue hover:text-signal-blue"
            >
              Acknowledge
            </button>
          )}
        </div>
      ))}
      {alerts.length === 0 && (
        <p className="text-sm text-asphalt-400">No active alerts.</p>
      )}
    </div>
  );
}
