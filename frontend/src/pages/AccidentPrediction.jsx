import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import {
  predictRouteAccident,
  getLatestAccidentPredictions,
  getAllRoads,
} from '../api_services';

const emptyForm = {
  road_id: '',
};

const RISK_BADGE_CLASS = {
  LOW: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  MEDIUM: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-400',
  HIGH: 'border-orange-500/40 bg-orange-500/10 text-orange-400',
  SEVERE: 'border-signal-red/40 bg-signal-red/10 text-signal-red',
  CRITICAL: 'border-signal-red/40 bg-signal-red/10 text-signal-red',
};

function RiskBadge({ level }) {
  const safeLevel = (level || 'LOW').toUpperCase();

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${
        RISK_BADGE_CLASS[safeLevel] || RISK_BADGE_CLASS.LOW
      }`}
    >
      {safeLevel}
    </span>
  );
}

export default function AccidentPrediction() {
  const [form, setForm] = useState(emptyForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const [recent, setRecent] = useState([]);
  const [recentLoading, setRecentLoading] = useState(true);
  const [roads, setRoads] = useState([]);
  const [roadsLoading, setRoadsLoading] = useState(true);
  const [roadsError, setRoadsError] = useState('');

  useEffect(() => {
    loadRecentPredictions();

    let isMounted = true;

    async function loadRoads() {
      setRoadsLoading(true);
      setRoadsError('');

      try {
        const data = await getAllRoads();
        if (isMounted) {
          setRoads(data);
          setForm((previous) => ({
            ...previous,
            road_id:
              previous.road_id && data.some((road) => road.road_id === previous.road_id)
                ? previous.road_id
                : data[0]?.road_id || '',
          }));
        }
      } catch {
        if (isMounted) {
          setRoadsError('Could not load roads from the database.');
        }
      } finally {
        if (isMounted) {
          setRoadsLoading(false);
        }
      }
    }

    loadRoads();
    const refreshTimer = window.setInterval(loadRoads, 30000);

    return () => {
      isMounted = false;
      window.clearInterval(refreshTimer);
    };
  }, []);

  async function loadRecentPredictions() {
    setRecentLoading(true);
    const data = await getLatestAccidentPredictions();
    setRecent(data);
    setRecentLoading(false);
  }

  function update(field, value) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setResult(null);

    const selectedRoad = roads.find((road) => road.road_id === form.road_id);
    if (!selectedRoad) {
      setError('Please select a road from the list.');
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        road_id: selectedRoad.road_id,
        start_location: selectedRoad.road_name,
        end_location: selectedRoad.road_name,
        persist: true,
      };

      const data = await predictRouteAccident(payload);

      setResult(data);
      await loadRecentPredictions();
    } catch (err) {
      if (err.response?.status === 404) {
        const detail = err.response.data?.detail;
        setError(
          (typeof detail === 'string' ? detail : detail?.message) ||
            'The selected route could not be found.'
        );
      } else if (err.response?.status === 422) {
        const detail = err.response.data?.detail;
        setError(
          Array.isArray(detail)
            ? detail.map((item) => item.msg).join(', ')
            : typeof detail === 'string'
              ? detail
              : detail?.message || 'The selected road does not have enough data for prediction.'
        );
      } else if (err.request) {
        setError('Unable to connect to the Accident Prediction service.');
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
        <h1 className="text-lg font-semibold text-asphalt-100">
          Accident Prediction
        </h1>

        <p className="mt-1 text-sm text-asphalt-400">
          Select a road from the database. RoadSense AI retrieves road, weather,
          traffic, and accident-history data from the backend to predict its risk.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6"
        >
          <label className={labelClass} htmlFor="road_id">
            Road *
          </label>

          <select
            id="road_id"
            required
            value={form.road_id}
            onChange={(event) =>
              update('road_id', event.target.value)
            }
            className={inputClass}
            disabled={roadsLoading || roads.length === 0}
          >
            <option value="">
              {roadsLoading ? 'Loading roads…' : 'Select a road'}
            </option>
            {roads.map((road) => (
              <option key={road.road_id} value={road.road_id}>
                {road.road_name}
              </option>
            ))}
          </select>

          {roadsError && (
            <p className="mt-2 text-xs text-signal-red">{roadsError}</p>
          )}

          <p className="mt-2 text-xs text-asphalt-500">
            This list is refreshed automatically every 30 seconds.
          </p>

          {error && (
            <p className="mt-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? 'Predicting…' : 'Predict Accident Risk'}
          </button>
        </form>

        <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-6">
          <p className="text-xs uppercase tracking-wide text-asphalt-400">
            Prediction Result
          </p>

          {!result && !isSubmitting && (
            <p className="mt-4 text-sm text-asphalt-400">
              Enter your route and run a prediction to see the result.
            </p>
          )}

          {isSubmitting && (
            <p className="mt-4 text-sm text-asphalt-400">
              Analyzing road, traffic, weather, and accident-history data…
            </p>
          )}

          {result && !isSubmitting && (
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-3">
                <RiskBadge level={result.risk_level} />
                <span className="text-sm text-asphalt-300">
                  {result.road_name || 'Selected route'}
                </span>
              </div>

              <div className="rounded-md border border-asphalt-700 bg-asphalt-950/50 p-4">
                <p className="text-xs text-asphalt-400">
                  Predicted accident risk
                </p>

                <p className="mt-1 text-3xl font-semibold text-asphalt-100">
                  {Number(result.risk_percentage).toFixed(1)}%
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-asphalt-400">Route</p>
                  <p className="text-asphalt-100">
                    {result.start_location} → {result.end_location}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-asphalt-400">Distance</p>
                  <p className="text-asphalt-100">
                    {result.distance_km != null
                      ? `${Number(result.distance_km).toFixed(1)} km`
                      : '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-asphalt-400">Confidence</p>
                  <p className="text-asphalt-100">
                    {result.confidence_score != null
                      ? `${Number(result.confidence_score).toFixed(1)}%`
                      : '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-asphalt-400">
                    Historical accidents
                  </p>
                  <p className="text-asphalt-100">
                    {result.historical_accidents_count ?? '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-asphalt-400">Weather</p>
                  <p className="text-asphalt-100">
                    {result.weather_conditions?.condition ||
                      result.weather_conditions?.weather_condition ||
                      '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-asphalt-400">
                    Prediction time
                  </p>
                  <p className="text-asphalt-100">
                    {result.prediction_time
                      ? new Date(result.prediction_time).toLocaleString()
                      : '—'}
                  </p>
                </div>
              </div>

              <div className="rounded-md border border-signal-blue/30 bg-signal-blue/10 p-3">
                <p className="text-xs font-medium text-signal-blue">
                  Safety Recommendation
                </p>

                <p className="mt-1 text-sm text-asphalt-200">
                  {(result.risk_level || '').toUpperCase() === 'SEVERE'
                    ? 'Critical accident hotspot corridor! Exercise extreme caution, sharply reduce speed, and consider taking a safer alternate route.'
                    : ['HIGH', 'CRITICAL'].includes((result.risk_level || '').toUpperCase())
                    ? 'Elevated accident risk corridor. Drive carefully, reduce speed, keep a safe braking distance, and avoid abrupt overtaking.'
                    : 'Follow normal road-safety practices, maintain safe speed, and stay alert while driving.'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs uppercase tracking-wide text-asphalt-400">
          Latest Accident Predictions
        </p>

        {recentLoading ? (
          <p className="text-sm text-asphalt-400">Loading…</p>
        ) : (
          <DataTable
            columns={[
              { key: 'road_name', header: 'Road' },
              {
                key: 'risk_level',
                header: 'Risk Level',
                render: (row) => <RiskBadge level={row.risk_level} />,
              },
              {
                key: 'risk_percentage',
                header: 'Risk',
                render: (row) =>
                  row.risk_percentage != null
                    ? `${Number(row.risk_percentage).toFixed(1)}%`
                    : '—',
              },
              {
                key: 'confidence_score',
                header: 'Confidence',
                render: (row) =>
                  row.confidence_score != null
                    ? `${Number(row.confidence_score).toFixed(1)}%`
                    : '—',
              },
              {
                key: 'prediction_time',
                header: 'Predicted At',
                render: (row) =>
                  row.prediction_time
                    ? new Date(row.prediction_time).toLocaleString()
                    : '—',
              },
            ]}
            rows={recent}
            emptyMessage="No accident predictions recorded yet."
          />
        )}
      </div>
    </div>
  );
}