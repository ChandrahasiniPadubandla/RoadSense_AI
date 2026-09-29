import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import LevelBadge from '../components/LevelBadge';
import DataTable from '../components/DataTable';

import {
  TRAFFIC_LEVEL_COLOR,
} from '../utils/constants';

import {
  geocodeSearch,
  predictRouteTraffic,
  getLatestTrafficPredictions,
} from '../api_services';


const emptyForm = {
  start_location: '',
  end_location: '',
  target_minutes_ahead: 30,
};


export default function TrafficPrediction() {

  // --------------------------------------------------
  // FORM
  // --------------------------------------------------

  const [form, setForm] = useState(emptyForm);


  // --------------------------------------------------
  // GEOCODING
  // --------------------------------------------------

  const [startLocations, setStartLocations] =
    useState([]);

  const [endLocations, setEndLocations] =
    useState([]);

  const [startSearching, setStartSearching] =
    useState(false);

  const [endSearching, setEndSearching] =
    useState(false);


  // --------------------------------------------------
  // REFS
  // --------------------------------------------------

  const startContainerRef = useRef(null);

  const endContainerRef = useRef(null);

  const endInputRef = useRef(null);


  // --------------------------------------------------
  // PREDICTION
  // --------------------------------------------------

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const [result, setResult] =
    useState(null);

  const [error, setError] =
    useState('');


  // --------------------------------------------------
  // RECENT PREDICTIONS
  // --------------------------------------------------

  const [recent, setRecent] =
    useState([]);

  const [recentLoading, setRecentLoading] =
    useState(true);


  // --------------------------------------------------
  // OUTSIDE CLICK
  // --------------------------------------------------

  useEffect(() => {

    function handleClickOutside(event) {

      if (
        startContainerRef.current &&
        !startContainerRef.current.contains(
          event.target
        )
      ) {
        setStartLocations([]);
      }

      if (
        endContainerRef.current &&
        !endContainerRef.current.contains(
          event.target
        )
      ) {
        setEndLocations([]);
      }
    }


    document.addEventListener(
      'mousedown',
      handleClickOutside
    );


    return () => {
      document.removeEventListener(
        'mousedown',
        handleClickOutside
      );
    };

  }, []);


  // --------------------------------------------------
  // INITIAL LOAD
  // --------------------------------------------------

  useEffect(() => {

    loadRecentPredictions();

  }, []);


  // --------------------------------------------------
  // START LOCATION GEOCODING
  // --------------------------------------------------

  useEffect(() => {

    const query =
      form.start_location.trim();


    if (query.length < 3) {

      setStartLocations([]);

      return;
    }


    const timer = setTimeout(
      async () => {

        try {

          setStartSearching(true);


          const results =
            await geocodeSearch(
              query,
              'Hyderabad',
              5
            );


          setStartLocations(
            Array.isArray(results)
              ? results
              : []
          );

        } catch (err) {

          console.error(
            'Start location geocoding failed:',
            err
          );

          setStartLocations([]);

        } finally {

          setStartSearching(false);

        }

      },
      400
    );


    return () =>
      clearTimeout(timer);

  }, [form.start_location]);


  // --------------------------------------------------
  // END LOCATION GEOCODING
  // --------------------------------------------------

  useEffect(() => {

    const query =
      form.end_location.trim();


    if (query.length < 3) {

      setEndLocations([]);

      return;
    }


    const timer = setTimeout(
      async () => {

        try {

          setEndSearching(true);


          const results =
            await geocodeSearch(
              query,
              'Hyderabad',
              5
            );


          setEndLocations(
            Array.isArray(results)
              ? results
              : []
          );

        } catch (err) {

          console.error(
            'End location geocoding failed:',
            err
          );

          setEndLocations([]);

        } finally {

          setEndSearching(false);

        }

      },
      400
    );


    return () =>
      clearTimeout(timer);

  }, [form.end_location]);


  // --------------------------------------------------
  // FORM UPDATE
  // --------------------------------------------------

  function update(field, value) {

    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));

  }


  // --------------------------------------------------
  // SELECT START LOCATION
  // --------------------------------------------------

  function selectStartLocation(location) {

    const locationName =
      location.display_name ||
      location.name ||
      '';


    update(
      'start_location',
      locationName
    );


    // Close suggestions
    setStartLocations([]);


    /*
     * Automatically move user
     * to End Location.
     */
    setTimeout(() => {

      endInputRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });


      endInputRef.current?.focus();

    }, 100);

  }


  // --------------------------------------------------
  // SELECT END LOCATION
  // --------------------------------------------------

  function selectEndLocation(location) {

    const locationName =
      location.display_name ||
      location.name ||
      '';


    update(
      'end_location',
      locationName
    );


    // Close suggestions
    setEndLocations([]);

  }


  // --------------------------------------------------
  // PAYLOAD
  // --------------------------------------------------

  function buildPayload() {

    return {

      start_location:
        form.start_location.trim(),

      end_location:
        form.end_location.trim(),

      target_minutes_ahead:
        Number(
          form.target_minutes_ahead
        ) || 30,

      persist: true,

    };

  }


  // --------------------------------------------------
  // RECENT PREDICTIONS
  // --------------------------------------------------

  async function loadRecentPredictions() {

    try {

      setRecentLoading(true);


      const data =
        await getLatestTrafficPredictions();


      setRecent(
        Array.isArray(data)
          ? data
          : []
      );

    } catch (err) {

      console.error(
        'Could not load recent predictions:',
        err
      );

      setRecent([]);

    } finally {

      setRecentLoading(false);

    }

  }


  // --------------------------------------------------
  // SUBMIT
  // --------------------------------------------------

  async function handleSubmit(e) {

    e.preventDefault();


    setError('');

    setResult(null);


    const start =
      form.start_location.trim();

    const end =
      form.end_location.trim();


    if (!start) {

      setError(
        'Please enter a start location.'
      );

      return;
    }


    if (!end) {

      setError(
        'Please enter an end location.'
      );

      return;
    }


    if (
      start.toLowerCase() ===
      end.toLowerCase()
    ) {

      setError(
        'Start location and end location must be different.'
      );

      return;
    }


    setIsSubmitting(true);


    try {

      const data =
        await predictRouteTraffic(
          buildPayload()
        );


      setResult(data);


      loadRecentPredictions();

    } catch (err) {

      console.error(
        'Traffic prediction error:',
        err
      );


      if (
        err.response?.status === 404
      ) {

        setError(
          err.response.data?.detail ||
          'That route could not be found.'
        );

      } else if (
        err.response?.status === 422
      ) {

        const detail =
          err.response.data?.detail;


        setError(
          Array.isArray(detail)
            ? detail
                .map((d) => d.msg)
                .join(', ')
            : 'Invalid input.'
        );

      } else if (
        err.response?.data?.detail
      ) {

        const detail =
          err.response.data.detail;


        setError(
          typeof detail === 'string'
            ? detail
            : detail.message ||
              detail.issue ||
              'Prediction failed.'
        );

      } else if (err.request) {

        setError(
          'Unable to connect to the Traffic Prediction service.'
        );

      } else {

        setError(
          err.message ||
          'Prediction failed.'
        );

      }

    } finally {

      setIsSubmitting(false);

    }

  }


  // --------------------------------------------------
  // STYLES
  // --------------------------------------------------

  const inputClass =
    'mt-1 w-full rounded-md border border-slate-300 dark:border-asphalt-600 bg-slate-100 dark:bg-asphalt-800 px-3 py-2 text-sm text-slate-900 dark:text-asphalt-100 outline-none focus:border-signal-blue';

  const labelClass =
    'block text-xs text-slate-500 dark:text-asphalt-400';


  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (

    <div className="space-y-6">

      {/* HEADER */}

      <div>

        <h1 className="text-lg font-semibold text-slate-900 dark:text-asphalt-100">
          Traffic Prediction
        </h1>

        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">

          Predicts congestion along a route between
          a start location and an end location,
          using RoadSense AI&rsquo;s traffic congestion
          prediction service.

        </p>

      </div>


      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">


        {/* ==================================================
            FORM
        ================================================== */}

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-slate-200 dark:border-asphalt-700 bg-white dark:bg-asphalt-900 p-6"
        >


          {/* START LOCATION */}

          <label
            className={labelClass}
            htmlFor="start_location"
          >
            Start Location *
          </label>


          <div
            ref={startContainerRef}
            className="relative"
          >

            <input
              id="start_location"
              type="text"
              required
              value={form.start_location}
              onChange={(e) => {

                update(
                  'start_location',
                  e.target.value
                );

                // Close end suggestions
                setEndLocations([]);

              }}
              className={inputClass}
              placeholder="e.g. Banjara Hills"
              autoComplete="off"
            />


            {startSearching && (

              <span className="absolute right-3 top-3 text-xs text-slate-400">
                Searching...
              </span>

            )}


            {/* START SUGGESTIONS */}

            {startLocations.length > 0 && (

              <div className="absolute left-0 right-0 z-50 mt-1 max-h-48 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900">

                {startLocations.map(
                  (location, index) => (

                    <button
                      key={
                        location.place_id ||
                        `${location.lat}-${location.lon}-${index}`
                      }
                      type="button"
                      onClick={() =>
                        selectStartLocation(
                          location
                        )
                      }
                      className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-slate-50 dark:border-asphalt-800 dark:hover:bg-asphalt-800"
                    >

                      <div className="font-medium text-slate-900 dark:text-asphalt-100">

                        {location.name ||
                          location.display_name}

                      </div>


                      {location.display_name && (

                        <div className="mt-1 text-xs text-slate-500 dark:text-asphalt-400">

                          {location.display_name}

                        </div>

                      )}

                    </button>

                  )
                )}

              </div>

            )}

          </div>


          {/* END LOCATION */}

          <label
            className={labelClass + ' mt-4'}
            htmlFor="end_location"
          >
            End Location *
          </label>


          <div
            ref={endContainerRef}
            className="relative"
          >

            <input
              ref={endInputRef}
              id="end_location"
              type="text"
              required
              value={form.end_location}
              onChange={(e) => {

                update(
                  'end_location',
                  e.target.value
                );

              }}
              className={inputClass}
              placeholder="e.g. Hitec City"
              autoComplete="off"
            />


            {endSearching && (

              <span className="absolute right-3 top-3 text-xs text-slate-400">
                Searching...
              </span>

            )}


            {/* END SUGGESTIONS */}

            {endLocations.length > 0 && (

              <div className="absolute left-0 right-0 z-50 mt-1 max-h-48 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900">

                {endLocations.map(
                  (location, index) => (

                    <button
                      key={
                        location.place_id ||
                        `${location.lat}-${location.lon}-${index}`
                      }
                      type="button"
                      onClick={() =>
                        selectEndLocation(
                          location
                        )
                      }
                      className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-slate-50 dark:border-asphalt-800 dark:hover:bg-asphalt-800"
                    >

                      <div className="font-medium text-slate-900 dark:text-asphalt-100">

                        {location.name ||
                          location.display_name}

                      </div>


                      {location.display_name && (

                        <div className="mt-1 text-xs text-slate-500 dark:text-asphalt-400">

                          {location.display_name}

                        </div>

                      )}

                    </button>

                  )
                )}

              </div>

            )}

          </div>


          {/* TARGET TIME */}

          <label
            className={labelClass + ' mt-4'}
            htmlFor="target_minutes_ahead"
          >
            Predict how many minutes ahead
          </label>


          <input
            id="target_minutes_ahead"
            type="number"
            min={5}
            max={1440}
            value={
              form.target_minutes_ahead
            }
            onChange={(e) =>
              update(
                'target_minutes_ahead',
                e.target.value
              )
            }
            className={inputClass}
          />


          {/* ERROR */}

          {error && (

            <p className="mt-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">

              {error}

            </p>

          )}


          {/* BUTTON */}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >

            {isSubmitting
              ? 'Predicting…'
              : 'Predict Traffic'}

          </button>

        </form>


        {/* ==================================================
            RESULT
        ================================================== */}

        <div className="rounded-lg border border-slate-200 dark:border-asphalt-700 bg-white dark:bg-asphalt-900 p-6">

          <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">
            Prediction Result
          </p>


          {!result && !isSubmitting && (

            <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">

              Enter a start and end location,
              then run a prediction to see
              the result here.

            </p>

          )}


          {isSubmitting && (

            <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">

              Running the model…

            </p>

          )}


          {result && !isSubmitting && (

            <div className="mt-4 space-y-4">


              <div className="flex flex-wrap items-center gap-3">

                <LevelBadge
                  level={result.congestion_level}
                  colorMap={TRAFFIC_LEVEL_COLOR}
                />

                <span className="text-sm text-slate-600 dark:text-asphalt-300">

                  {result.start_location}
                  {' → '}
                  {result.end_location}

                </span>

              </div>


              <div className="flex flex-wrap items-center justify-between gap-2">

                <p className="text-xs text-slate-500 dark:text-asphalt-400">

                  Matched road:{' '}

                  <span className="text-slate-800 dark:text-asphalt-200 font-medium">

                    {result.road_name}

                  </span>

                </p>


                {result.ml_source && (

                  <span className="inline-flex items-center rounded-full bg-emerald-950/60 border border-emerald-500/30 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">

                    ⚡ {result.ml_source}

                  </span>

                )}

              </div>


              {/* ANOMALY */}

              {result.anomaly_detection && (

                <div
                  className={`rounded-lg border p-3.5 transition-all ${
                    result.anomaly_detection.is_anomaly
                      ? 'border-rose-500/40 bg-rose-950/20 text-rose-300'
                      : 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
                  }`}
                >

                  <div className="flex items-center justify-between">

                    <div className="flex items-center gap-2">

                      <span className="text-sm">

                        {result.anomaly_detection.is_anomaly
                          ? '⚠️'
                          : '✓'}

                      </span>

                      <span className="text-xs font-semibold text-asphalt-100">

                        Traffic Anomaly Analysis

                      </span>

                    </div>


                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        result.anomaly_detection.is_anomaly
                          ? 'border border-rose-500/40 bg-rose-500/20 text-rose-300'
                          : 'border border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                      }`}
                    >

                      {
                        result.anomaly_detection
                          .prediction
                      }

                    </span>

                  </div>


                  <p className="mt-1.5 text-[11px] text-asphalt-300">

                    {result.anomaly_detection.is_anomaly

                      ? 'Unusual traffic pattern or unexpected volume surge detected along this corridor.'

                      : 'Traffic patterns are conforming to normal historical parameters.'}


                    {result.anomaly_detection.anomaly_score != null && (

                      <span className="text-asphalt-400 font-mono ml-1">

                        (
                        score:{' '}
                        {result.anomaly_detection.anomaly_score.toFixed(
                          4
                        )}
                        )

                      </span>

                    )}

                  </p>

                </div>

              )}


              {/* METRICS */}

              <div className="grid grid-cols-2 gap-3 text-sm">

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Estimated time window
                  </p>

                  <p className="text-slate-900 dark:text-asphalt-100">
                    {result.estimated_time}
                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Confidence
                  </p>

                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.confidence_score != null
                      ? `${result.confidence_score.toFixed(
                          1
                        )}%`
                      : '—'}

                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Distance
                  </p>

                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.distance_km != null
                      ? `${result.distance_km} km`
                      : '—'}

                  </p>

                </div>


                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">
                    Target time
                  </p>

                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.target_time
                      ? new Date(
                          result.target_time
                        ).toLocaleString()
                      : '—'}

                  </p>

                </div>

              </div>


              {/* WEATHER */}

              {result.weather_conditions &&
                Object.keys(
                  result.weather_conditions
                ).length > 0 && (

                  <div>

                    <p className="text-xs text-slate-500 dark:text-asphalt-400">
                      Weather along route
                    </p>

                    <p className="mt-1 text-sm text-slate-800 dark:text-asphalt-200">

                      {result.weather_conditions
                        .weather_condition ?? '—'}

                      {result.weather_conditions
                        .temperature != null &&
                        ` · ${result.weather_conditions.temperature}°C`}

                      {result.weather_conditions
                        .rainfall != null &&
                        ` · ${result.weather_conditions.rainfall}mm rain`}

                    </p>

                  </div>

                )}


              {/* ROAD CONDITIONS */}

              {result.road_conditions &&
                Object.keys(
                  result.road_conditions
                ).length > 0 && (

                  <div>

                    <p className="text-xs text-slate-500 dark:text-asphalt-400">
                      Road conditions
                    </p>

                    <p className="mt-1 text-sm text-slate-800 dark:text-asphalt-200">

                      {result.road_conditions
                        .road_type ?? '—'}

                      {result.road_conditions
                        .speed_limit != null &&
                        ` · ${result.road_conditions.speed_limit} km/h limit`}

                      {result.road_conditions
                        .number_of_lanes != null &&
                        ` · ${result.road_conditions.number_of_lanes} lanes`}

                      {result.road_conditions
                        .road_condition &&
                        ` · ${result.road_conditions.road_condition}`}

                    </p>

                  </div>

                )}

            </div>

          )}

        </div>

      </div>


      {/* ==================================================
          RECENT PREDICTIONS
      ================================================== */}

      <div>

        <p className="mb-2 text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">

          Latest Predictions (all roads)

        </p>


        {recentLoading ? (

          <p className="text-sm text-slate-500 dark:text-asphalt-400">
            Loading…
          </p>

        ) : (

          <DataTable

            columns={[

              {
                key: 'road_name',
                header: 'Road',
              },

              {
                key: 'congestion_level',
                header: 'Congestion',

                render: (row) => (

                  <LevelBadge
                    level={row.congestion_level}
                    colorMap={TRAFFIC_LEVEL_COLOR}
                  />

                ),
              },

              {
                key: 'estimated_time',
                header: 'Estimated Time',
              },

              {
                key: 'confidence_score',
                header: 'Confidence',

                render: (row) =>
                  row.confidence_score != null
                    ? `${row.confidence_score.toFixed(
                        1
                      )}%`
                    : '—',
              },

              {
                key: 'target_time',
                header: 'Target Time',

                render: (row) =>
                  row.target_time
                    ? new Date(
                        row.target_time
                      ).toLocaleString()
                    : '—',
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