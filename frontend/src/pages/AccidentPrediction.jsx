import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import {
  predictRouteAccident,
  getLatestAccidentPredictions,
} from '../api_services';

const emptyForm = {
<<<<<<< HEAD
  from_road_id: '',
  to_road_id: '',
=======
  start_location: '',
  end_location: '',
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
};

const RISK_BADGE_CLASS = {
  LOW: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  MEDIUM: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-400',
  HIGH: 'border-orange-500/40 bg-orange-500/10 text-orange-400',
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

  useEffect(() => {
    loadRecentPredictions();
<<<<<<< HEAD

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
            from_road_id:
              previous.from_road_id &&
              data.some((road) => road.road_id === previous.from_road_id)
                ? previous.from_road_id
                : '',
            to_road_id:
              previous.to_road_id &&
              data.some((road) => road.road_id === previous.to_road_id)
                ? previous.to_road_id
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
=======
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
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

<<<<<<< HEAD
    const fromRoad = roads.find((road) => road.road_id === form.from_road_id);
    const toRoad = roads.find((road) => road.road_id === form.to_road_id);
    if (!fromRoad || !toRoad) {
      setError('Please select both a From road and a To road.');
      return;
    }
    if (fromRoad.road_id === toRoad.road_id) {
      setError('From road and To road must be different.');
=======
    if (!form.start_location.trim() || !form.end_location.trim()) {
      setError('Please enter both the starting point and destination.');
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
<<<<<<< HEAD
        start_location: fromRoad.road_name,
        end_location: toRoad.road_name,
=======
        start_location: form.start_location.trim(),
        end_location: form.end_location.trim(),
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
        persist: true,
      };

      if (
        fromRoad.start_latitude != null &&
        fromRoad.start_longitude != null
      ) {
        payload.start_latitude = Number(fromRoad.start_latitude);
        payload.start_longitude = Number(fromRoad.start_longitude);
      }

      if (toRoad.end_latitude != null && toRoad.end_longitude != null) {
        payload.end_latitude = Number(toRoad.end_latitude);
        payload.end_longitude = Number(toRoad.end_longitude);
      }

      const data = await predictRouteAccident(payload);

      setResult({
        ...data,
        from_road_name: data.start_location || fromRoad.road_name,
        to_road_name: data.end_location || toRoad.road_name,
      });
      await loadRecentPredictions();
    } catch (err) {
      if (err.response?.status === 404) {
        setError(
          err.response.data?.detail ||
            'The selected route could not be found.'
        );
      } else if (err.response?.status === 422) {
        const detail = err.response.data?.detail;
        setError(
          Array.isArray(detail)
            ? detail.map((item) => item.msg).join(', ')
            : 'Please enter valid locations.'
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
    'mt-1 w-full rounded-md border border-slate-300 dark:border-asphalt-600 bg-slate-100 dark:bg-asphalt-800 px-3 py-2 text-sm text-slate-900 dark:text-asphalt-100 outline-none focus:border-signal-blue';

  const labelClass = 'block text-xs text-slate-500 dark:text-asphalt-400';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-asphalt-100">
          Accident Prediction
        </h1>

<<<<<<< HEAD
        <p className="mt-1 text-sm text-asphalt-400">
          Select a From and To road. RoadSense AI calculates the route between
          them and uses road, weather, traffic, and accident-history data to
          predict accident risk.
=======
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Enter a starting point and destination. RoadSense AI retrieves road,
          weather, traffic, and accident-history data from the backend to
          predict route risk.
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-slate-200 dark:border-asphalt-700 bg-white dark:bg-asphalt-900 p-6"
        >
<<<<<<< HEAD
          <label className={labelClass} htmlFor="from_road_id">
            From Road *
          </label>

          <select
            id="from_road_id"
            required
            value={form.from_road_id}
            onChange={(event) =>
              update('from_road_id', event.target.value)
=======
          <label className={labelClass} htmlFor="start_location">
            Starting Point *
          </label>

          <input
            id="start_location"
            type="text"
            required
            value={form.start_location}
            onChange={(event) =>
              update('start_location', event.target.value)
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
            }
            className={inputClass}
            placeholder="Example: Banjara Hills"
          />

<<<<<<< HEAD
          <label className={`${labelClass} mt-4`} htmlFor="to_road_id">
            To Road *
          </label>

          <select
            id="to_road_id"
            required
            value={form.to_road_id}
            onChange={(event) => update('to_road_id', event.target.value)}
            className={inputClass}
            disabled={roadsLoading || roads.length === 0}
          >
            <option value="">
              {roadsLoading ? 'Loading roads…' : 'Select a destination road'}
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
=======
          <label className={`${labelClass} mt-4`} htmlFor="end_location">
            Destination *
          </label>
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386

          <input
            id="end_location"
            type="text"
            required
            value={form.end_location}
            onChange={(event) => update('end_location', event.target.value)}
            className={inputClass}
            placeholder="Example: Hitec City"
          />

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

        <div className="rounded-lg border border-slate-200 dark:border-asphalt-700 bg-white dark:bg-asphalt-900 p-6">
          <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">
            Prediction Result
          </p>

          {!result && !isSubmitting && (
<<<<<<< HEAD
            <p className="mt-4 text-sm text-asphalt-400">
              Select both roads and run a prediction to see the result.
=======
            <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">
              Enter your route and run a prediction to see the result.
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
            </p>
          )}

          {isSubmitting && (
            <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">
              Analyzing road, traffic, weather, and accident-history data…
            </p>
          )}

          {result && !isSubmitting && (
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-3">
<<<<<<< HEAD
                <RiskBadge
                  level={result.risk_level || result.accident_risk_level}
                />
                <span className="text-sm text-asphalt-300">
                {result.road_name || 'Selected road'}
=======
                <RiskBadge level={result.risk_level} />
                <span className="text-sm text-slate-600 dark:text-asphalt-300">
                  {result.road_name || 'Selected route'}
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
                </span>
              </div>

              <div className="rounded-md border border-slate-200 dark:border-asphalt-700 bg-slate-50 dark:bg-asphalt-950/50 p-4">
                <p className="text-xs text-slate-500 dark:text-asphalt-400">
                  Predicted accident risk
                </p>

<<<<<<< HEAD
                <p className="mt-1 text-3xl font-semibold text-asphalt-100">
                  {Number(result.risk_percentage ?? result.accident_risk).toFixed(1)}%
=======
                <p className="mt-1 text-3xl font-semibold text-slate-900 dark:text-asphalt-100">
                  {Number(result.risk_percentage).toFixed(1)}%
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
<<<<<<< HEAD
                  <p className="text-xs text-asphalt-400">Route</p>
                  <p className="text-asphalt-100">
                    {result.from_road_name || result.start_location} →{' '}
                    {result.to_road_name || result.end_location}
=======
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">Route</p>
                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.start_location} → {result.end_location}
>>>>>>> 7222f1e6bceae26fff4fad7af174e13e00df8386
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">Distance</p>
                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.distance_km != null
                      ? `${Number(result.distance_km).toFixed(1)} km`
                      : '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">Confidence</p>
                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.confidence_score != null
                      ? `${Number(result.confidence_score).toFixed(1)}%`
                      : '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Historical accidents
                  </p>
                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.historical_accidents_count ?? '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">Weather</p>
                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.weather_conditions?.condition ||
                      result.weather_conditions?.weather_condition ||
                      '—'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Prediction time
                  </p>
                  <p className="text-slate-900 dark:text-asphalt-100">
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

                <p className="mt-1 text-sm text-slate-800 dark:text-asphalt-200">
                  {['HIGH', 'CRITICAL'].includes(
                    (result.risk_level || '').toUpperCase()
                  )
                    ? 'Drive carefully, reduce speed, keep a safe distance, and consider an alternative route.'
                    : 'Follow normal road-safety practices and stay alert while driving.'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">
          Latest Accident Predictions
        </p>

        {recentLoading ? (
          <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading…</p>
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