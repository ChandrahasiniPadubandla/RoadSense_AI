import React, { useEffect, useState } from 'react';
import * as emergencyResponseService from '../api/emergencyResponseService';

const STATUS_FLOW = ['PENDING', 'EN_ROUTE', 'ON_SCENE', 'RESOLVED'];

const STATUS_STYLES = {
  PENDING: 'border-signal-amber/40 bg-signal-amber/10 text-signal-amber',
  EN_ROUTE: 'border-signal-blue/40 bg-signal-blue/10 text-signal-blue',
  ON_SCENE: 'border-signal-blue/40 bg-signal-blue/10 text-signal-blue',
  RESOLVED: 'border-signal-green/40 bg-signal-green/10 text-signal-green',
};

export default function EmergencyResponse() {
  const [responses, setResponses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  function load() {
    return emergencyResponseService.getEmergencyResponses().then((data) => {
      setResponses(data);
      setIsLoading(false);
    });
  }

  useEffect(() => {
    load();
  }, []);

  function nextStatus(current) {
    const idx = STATUS_FLOW.indexOf(current);
    return idx >= 0 && idx < STATUS_FLOW.length - 1 ? STATUS_FLOW[idx + 1] : null;
  }

  async function handleAdvance(response) {
    const next = nextStatus(response.status);
    if (!next) return;
    setUpdatingId(response.id);
    try {
      await emergencyResponseService.updateResponseStatus(response.id, next);
      await load();
    } finally {
      setUpdatingId(null);
    }
  }

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading dispatch board…</p>;

  return (
    <div className="space-y-3">
      <p className="text-sm text-asphalt-400">
        Track and advance emergency response status for reported accidents.
      </p>
      {responses.map((r) => {
        const next = nextStatus(r.status);
        return (
          <div
            key={r.id}
            className="flex items-start justify-between rounded-lg border border-asphalt-700 bg-asphalt-900 p-4"
          >
            <div>
              <p className="text-sm font-medium text-asphalt-100">{r.accidentLocation}</p>
              <p className="mt-1 text-xs text-asphalt-400">
                Assigned to: {r.assignedUserName}
                {r.assignedAt && ` · dispatched ${new Date(r.assignedAt).toLocaleTimeString()}`}
              </p>
              {r.notes && <p className="mt-1 text-xs text-asphalt-400">{r.notes}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                  STATUS_STYLES[r.status] || 'border-asphalt-600 text-asphalt-300'
                }`}
              >
                {r.status.replace('_', ' ')}
              </span>
              {next && (
                <button
                  onClick={() => handleAdvance(r)}
                  disabled={updatingId === r.id}
                  className="rounded-md border border-asphalt-600 px-3 py-1.5 text-xs text-asphalt-200 hover:border-signal-blue hover:text-signal-blue disabled:opacity-50"
                >
                  {updatingId === r.id ? 'Updating…' : `Mark ${next.replace('_', ' ')}`}
                </button>
              )}
            </div>
          </div>
        );
      })}
      {responses.length === 0 && (
        <p className="text-sm text-asphalt-400">No active emergency responses.</p>
      )}
    </div>
  );
}
