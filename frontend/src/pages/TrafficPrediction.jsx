import React, { useEffect, useState } from 'react';
import LevelBadge from '../components/LevelBadge';
import DataTable from '../components/DataTable';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import { getRoads, predictTraffic, getLatestTrafficPredictions } from '../api_services';

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Foggy', 'Overcast'];
const ROAD_CONDITION_OPTIONS = ['Good', 'Fair', 'Poor', 'Wet'];

const emptyForm = {
  road_id: '',
  target_minutes_ahead: 30,
  vehicle_count: '',
  average_speed: '',
  traffic_density: '',
  weather: '',
  rainfall: '',
  temperature: '',
  road_condition: '',
  is_holiday: false,
};

/**
 * Traffic Prediction page (DPR Module 3).
 *
 * Flow:
 *   TrafficPrediction.jsx
 *     -> api_services.js: getRoads()              (GET /api/roads)
 *     -> api_services.js: predictTraffic(payload)  (POST /api/predictions/traffic/predict)
 *     -> api_services.js: getLatestTrafficPredictions() (GET /api/predictions/traffic/latest)
 *
 * No mock data anywhere on this page: roads come from the real /api/roads
 * endpoint, and the prediction result is exactly what the FastAPI
 * TrafficPredictionRunResponse returns — nothing is invented client-side.
 */
export default function TrafficPrediction() {
  const [roads, setRoads] = useState([]);
  const [roadsLoading, setRoadsLoading] = useState(true);
  const [roadsError, setRoadsError] = useState('');

  const [form, setForm] = useState(emptyForm);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const [recent, setRecent] = useState([]);
  const [recentLoading, setRecentLoading] = useState(true);

  useEffect(() => {
    loadRoads();
    loadRecentPredictions();
  }, []);

  async function loadRoads() {
    setRoadsLoading(true);
    setRoadsError('');
    try {
      const data = await getRoads();
      setRoads(data);
      if (data.length === 0) {
        setRoadsError('No roads found. Ask a Super Admin to add roads before running predictions.');
      }
    } catch (err) {
      setRoadsError('Unable to load roads from the server.');
    } finally {
      setRoadsLoading(false);
    }
  }

  async function loadRecentPredictions() {
    setRecentLoading(true);
    const data = await getLatestTrafficPredictions();
    setRecent(data);
    setRecentLoading(false);
  }

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function buildPayload() {
    // Only include optional fields the user actually filled in — the
    // backend treats missing fields as "let the model/engine decide",
    // so we must not send empty strings for numeric/optional fields.
    const payload = {
      road_id: form.road_id,
      target_minutes_ahead: Number(form.target_minutes_ahead) || 30,
      is_holiday: Boolean(form.is_holiday),
      persist: true,
    };
    if (form.vehicle_count !== '') payload.vehicle_count = Number(form.vehicle_count);
    if (form.average_speed !== '') payload.average_speed = Number(form.average_speed);
    if (form.traffic_density !== '') payload.traffic_density = Number(form.traffic_density);
    if (form.weather !== '') payload.weather = form.weather;
    if (form.rainfall !== '') payload.rainfall = Number(form.rainfall);
    if (form.temperature !== '') payload.temperature = Number(form.temperature);
    if (form.road_condition !== '') payload.road_condition = form.road_condition;
    return payload;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setResult(null);

    if (!form.road_id) {
      setError('Please select a road.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await predictTraffic(buildPayload());
      setResult(data);
      loadRecentPredictions();
    } catch (err) {
      if (err.response?.status === 404) {
        setError(err.response.data?.detail || 'That road could not be found.');
      } else if (err.response?.status === 422) {
        const detail = err.response.data?.detail;
        setError(Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : 'Invalid input.');
      } else if (err.request) {
        setError('Unable to connect to the Traffic Prediction service.');
      } else {
        setError(err.message || 'Prediction failed.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputClass =
    'mt-1 w-full rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue';
  const labelClass = 'block text-xs text-asphalt-400';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-asphalt-100">Traffic Prediction</h1>
        <p className="mt-1 text-sm text-asphalt-400">
          Predicts future congestion for a selected road using RoadSense AI&rsquo;s traffic
          congestion prediction service. Select a road and, optionally, current
          conditions — the backend fills in anything you leave blank from the
          latest recorded telemetry for that road.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* -------------------- FORM -------------------- */}
        <form onSubmit={handleSubmit} className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6">
          <label className={labelClass} htmlFor="road_id">Road *</label>
          {roadsLoading ? (
            <p className="mt-1 text-sm text-asphalt-400">Loading roads…</p>
          ) : (
            <select
              id="road_id"
              required
              value={form.road_id}
              onChange={(e) => update('road_id', e.target.value)}
              className={inputClass}
            >
              <option value="">Select a road…</option>
              {roads.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          )}
          {roadsError && <p className="mt-1 text-xs text-signal-red">{roadsError}</p>}

          <label className={labelClass + ' mt-4'} htmlFor="target_minutes_ahead">
            Predict how many minutes ahead
          </label>
          <input
            id="target_minutes_ahead"
            type="number"
            min={5}
            max={1440}
            value={form.target_minutes_ahead}
            onChange={(e) => update('target_minutes_ahead', e.target.value)}
            className={inputClass}
          />

          <button
            type="button"
            onClick={() => setShowAdvanced((s) => !s)}
            className="mt-4 text-xs text-signal-blue hover:underline"
          >
            {showAdvanced ? '− Hide current conditions (optional)' : '+ Add current conditions (optional)'}
          </button>

          {showAdvanced && (
            <div className="mt-3 grid grid-cols-2 gap-3 rounded-md border border-asphalt-800 bg-asphalt-950/50 p-3">
              <div>
                <label className={labelClass} htmlFor="vehicle_count">Vehicle count</label>
                <input id="vehicle_count" type="number" min={0} value={form.vehicle_count}
                  onChange={(e) => update('vehicle_count', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor="average_speed">Average speed (km/h)</label>
                <input id="average_speed" type="number" min={0} step="0.1" value={form.average_speed}
                  onChange={(e) => update('average_speed', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor="traffic_density">Traffic density (%)</label>
                <input id="traffic_density" type="number" min={0} max={100} step="0.1" value={form.traffic_density}
                  onChange={(e) => update('traffic_density', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor="weather">Weather</label>
                <select id="weather" value={form.weather} onChange={(e) => update('weather', e.target.value)} className={inputClass}>
                  <option value="">Use latest recorded</option>
                  {WEATHER_OPTIONS.map((w) => <option key={w} value={w}>{w}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass} htmlFor="rainfall">Rainfall (mm)</label>
                <input id="rainfall" type="number" min={0} step="0.1" value={form.rainfall}
                  onChange={(e) => update('rainfall', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor="temperature">Temperature (°C)</label>
                <input id="temperature" type="number" step="0.1" value={form.temperature}
                  onChange={(e) => update('temperature', e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass} htmlFor="road_condition">Road condition</label>
                <select id="road_condition" value={form.road_condition} onChange={(e) => update('road_condition', e.target.value)} className={inputClass}>
                  <option value="">Use latest recorded</option>
                  {ROAD_CONDITION_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex items-end gap-2 pb-2">
                <input id="is_holiday" type="checkbox" checked={form.is_holiday}
                  onChange={(e) => update('is_holiday', e.target.checked)}
                  className="h-4 w-4 rounded border-asphalt-600 bg-asphalt-800" />
                <label htmlFor="is_holiday" className="text-xs text-asphalt-300">Is holiday</label>
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting || roadsLoading || roads.length === 0}
            className="mt-5 w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? 'Predicting…' : 'Predict Traffic'}
          </button>
        </form>

        {/* -------------------- RESULT -------------------- */}
        <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6">
          <p className="text-xs uppercase tracking-wide text-asphalt-400">Prediction Result</p>

          {!result && !isSubmitting && (
            <p className="mt-4 text-sm text-asphalt-400">
              Run a prediction to see the result here.
            </p>
          )}

          {isSubmitting && <p className="mt-4 text-sm text-asphalt-400">Running the model…</p>}

          {result && !isSubmitting && (
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-3">
                <LevelBadge level={result.congestion_level} colorMap={TRAFFIC_LEVEL_COLOR} />
                <span className="text-sm text-asphalt-300">on {result.road_name}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-asphalt-400">Estimated time window</p>
                  <p className="text-asphalt-100">{result.estimated_time}</p>
                </div>
                <div>
                  <p className="text-xs text-asphalt-400">Confidence</p>
                  <p className="text-asphalt-100">
                    {result.confidence_score != null ? `${result.confidence_score.toFixed(1)}%` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-asphalt-400">Predicted vehicle count</p>
                  <p className="text-asphalt-100">{result.predicted_vehicle_count ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-asphalt-400">Target time</p>
                  <p className="text-asphalt-100">
                    {result.target_time ? new Date(result.target_time).toLocaleString() : '—'}
                  </p>
                </div>
              </div>

              {result.class_probabilities && Object.keys(result.class_probabilities).length > 0 && (
                <div>
                  <p className="text-xs text-asphalt-400">Class probabilities</p>
                  <ul className="mt-1 space-y-1 text-sm text-asphalt-200">
                    {Object.entries(result.class_probabilities).map(([level, pct]) => (
                      <li key={level} className="flex justify-between">
                        <span>{level}</span>
                        <span>{Number(pct).toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* -------------------- RECENT PREDICTIONS -------------------- */}
      <div>
        <p className="mb-2 text-xs uppercase tracking-wide text-asphalt-400">
          Latest Predictions (all roads)
        </p>
        {recentLoading ? (
          <p className="text-sm text-asphalt-400">Loading…</p>
        ) : (
          <DataTable
            columns={[
              { key: 'road_name', header: 'Road' },
              {
                key: 'congestion_level',
                header: 'Congestion',
                render: (row) => <LevelBadge level={row.congestion_level} colorMap={TRAFFIC_LEVEL_COLOR} />,
              },
              { key: 'estimated_time', header: 'Estimated Time' },
              {
                key: 'confidence_score',
                header: 'Confidence',
                render: (row) => (row.confidence_score != null ? `${row.confidence_score.toFixed(1)}%` : '—'),
              },
              {
                key: 'target_time',
                header: 'Target Time',
                render: (row) => (row.target_time ? new Date(row.target_time).toLocaleString() : '—'),
              },
            ]}
            rows={recent}
            emptyMessage="No traffic predictions recorded yet."
          />
        )}
      </div>
    </div>
  );
}
