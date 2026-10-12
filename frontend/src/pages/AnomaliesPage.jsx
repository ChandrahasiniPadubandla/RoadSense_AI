import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import { getAnomalies, getRoads, predictAnomaly } from '../api_services';

const emptyForm = { road_id: '', vehicle_count: '', average_speed: '', traffic_density: '', road_capacity: '', previous_traffic: '', hour: '' };

function StatusBadge({ status, isAnomaly }) {
  const value = status || (isAnomaly ? 'ANOMALY' : 'NORMAL');
  const alert = ['ACTIVE', 'ANOMALY'].includes(value.toUpperCase());
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${alert ? 'border-signal-red/40 bg-signal-red/10 text-signal-red' : 'border-signal-green/40 bg-signal-green/10 text-signal-green'}`}>{value}</span>;
}

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState([]);
  const [roads, setRoads] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [roadsLoading, setRoadsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  async function loadAnomalies() {
    setLoading(true);
    try { setAnomalies(await getAnomalies(100)); }
    catch { setError('Could not load recorded anomalies from the server.'); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    loadAnomalies();
    (async () => {
      try { setRoads(await getRoads()); }
      catch { setError('Could not load roads for anomaly analysis.'); }
      finally { setRoadsLoading(false); }
    })();
  }, []);

  function update(field, value) { setForm((current) => ({ ...current, [field]: value })); }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setResult(null);
    if (!form.road_id) {
      setError('Please select a road. The latest telemetry will be used automatically.');
      return;
    }
    const payload = {
      road_id: form.road_id,
      persist: true,
      ...Object.fromEntries(Object.entries(form).filter(([key, value]) => key !== 'road_id' && value !== '').map(([key, value]) => [key, Number(value)])),
    };
    setSubmitting(true);
    try {
      setResult(await predictAnomaly(payload));
      await loadAnomalies();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : detail || 'Anomaly prediction failed.');
    } finally { setSubmitting(false); }
  }

  const inputClass = 'mt-1 w-full rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-800 dark:text-asphalt-100';
  const labelClass = 'block text-xs text-slate-500 dark:text-asphalt-400';
  const optionalFields = [
    ['vehicle_count', 'Vehicle count', 0], ['average_speed', 'Average speed (km/h)', 0],
    ['traffic_density', 'Traffic density (%)', 0], ['road_capacity', 'Road capacity', 1],
    ['previous_traffic', 'Previous traffic', 0], ['hour', 'Hour (0–23)', 0, 23],
  ];

  return <div className="space-y-6">
    <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
      <h1 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">Traffic Anomalies</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">Review unusual traffic patterns detected by the trained anomaly model, or analyse a road using its latest telemetry.</p>
    </div>

    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-6 dark:border-asphalt-700 dark:bg-asphalt-900">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-asphalt-400">Run analysis</p>
        <label className={`${labelClass} mt-4`} htmlFor="anomaly-road">Road *</label>
        <select id="anomaly-road" required value={form.road_id} onChange={(event) => update('road_id', event.target.value)} className={inputClass} disabled={roadsLoading}>
          <option value="">{roadsLoading ? 'Loading roads…' : 'Select a road'}</option>
          {roads.map((road) => <option key={road.id} value={road.id}>{road.name}</option>)}
        </select>
        {!roadsLoading && roads.length === 0 && <p className="mt-2 text-xs text-signal-red">No roads are available. Add roads or check the backend connection.</p>}
        <p className="mt-5 text-xs text-slate-500 dark:text-asphalt-400">Optional values override the road’s latest recorded telemetry.</p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {optionalFields.map(([field, label, min, max]) => <label key={field} className={labelClass}>{label}
            <input type="number" min={min} max={max} value={form[field]} onChange={(event) => update(field, event.target.value)} className={inputClass} />
          </label>)}
        </div>
        {error && <p className="mt-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">{error}</p>}
        <button type="submit" disabled={submitting || roadsLoading || roads.length === 0} className="mt-5 w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50">{submitting ? 'Analysing…' : 'Analyse Traffic'}</button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-white p-6 dark:border-asphalt-700 dark:bg-asphalt-900">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-asphalt-400">Analysis result</p>
        {!result && !submitting && <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">Select a road and run an analysis to see the ML result here.</p>}
        {submitting && <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">Checking traffic conditions with the anomaly model…</p>}
        {result && !submitting && <div className="mt-4 space-y-4">
          <div className="flex items-center gap-3"><StatusBadge isAnomaly={result.is_anomaly} /><span className="text-sm text-slate-700 dark:text-asphalt-200">{result.road_name || 'Selected road'}</span></div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><p className="text-xs text-slate-500 dark:text-asphalt-400">Anomaly score</p><p className="mt-1 text-xl font-semibold text-slate-900 dark:text-asphalt-100">{result.anomaly_score != null ? Number(result.anomaly_score).toFixed(4) : '—'}</p></div>
            <div><p className="text-xs text-slate-500 dark:text-asphalt-400">Confidence</p><p className="mt-1 text-xl font-semibold text-slate-900 dark:text-asphalt-100">{result.confidence_score != null ? `${Number(result.confidence_score).toFixed(1)}%` : '—'}</p></div>
          </div>
          <div className="rounded-md border border-signal-blue/30 bg-signal-blue/10 p-3 text-sm text-slate-800 dark:text-asphalt-200">{result.is_anomaly ? 'Unusual traffic behaviour was detected. Review this road and consider raising an alert.' : 'No unusual traffic behaviour was detected for the analysed conditions.'}</div>
        </div>}
      </div>
    </div>

    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-asphalt-400">Recent detections</p>
      {loading ? <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading anomalies…</p> : <DataTable rows={anomalies} emptyMessage="No traffic anomalies have been recorded yet." columns={[
        { key: 'road_name', header: 'Road', render: (row) => row.road_name || 'Unknown road' },
        { key: 'anomaly_type', header: 'Type', render: (row) => row.anomaly_type || '—' },
        { key: 'anomaly_score', header: 'Score', render: (row) => row.anomaly_score != null ? Number(row.anomaly_score).toFixed(4) : '—' },
        { key: 'actual_vehicle_count', header: 'Vehicles', render: (row) => row.actual_vehicle_count ?? '—' },
        { key: 'detected_at', header: 'Detected', render: (row) => row.detected_at ? new Date(row.detected_at).toLocaleString() : '—' },
        { key: 'status', header: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]} />}
    </div>
  </div>;
}
