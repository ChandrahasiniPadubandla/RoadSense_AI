import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import DataTable from '../components/DataTable';
import VoiceAssistant from '../components/VoiceAssistant';

import {
  geocodeSearch,
  predictRouteAccident,
  getLatestAccidentPredictions,
} from '../api_services';


const emptyForm = {
  start_location: '',
  end_location: '',
};


const RISK_BADGE_CLASS = {
  LOW: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  MEDIUM: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-400',
  HIGH: 'border-orange-500/40 bg-orange-500/10 text-orange-400',
  CRITICAL: 'border-signal-red/40 bg-signal-red/10 text-signal-red',
};


function RiskBadge({ level }) {
  const safeLevel =
    (level || 'LOW').toUpperCase();

  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${
        RISK_BADGE_CLASS[safeLevel] ||
        RISK_BADGE_CLASS.LOW
      }`}
    >
      {safeLevel}
    </span>
  );
}


export default function AccidentPrediction() {

  // ==================================================
  // FORM
  // ==================================================

  const [form, setForm] =
    useState(emptyForm);


  // ==================================================
  // GEOCODE SUGGESTIONS
  // ==================================================

  const [startLocations, setStartLocations] =
    useState([]);

  const [endLocations, setEndLocations] =
    useState([]);


  // ==================================================
  // SEARCH TEXT
  // ==================================================

  const [startSearch, setStartSearch] =
    useState('');

  const [endSearch, setEndSearch] =
    useState('');


  const [startSearching, setStartSearching] =
    useState(false);

  const [endSearching, setEndSearching] =
    useState(false);


  // ==================================================
  // ERROR / PREDICTION
  // ==================================================

  const [roadsError, setRoadsError] =
    useState('');

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const [result, setResult] =
    useState(null);

  const [error, setError] =
    useState('');


  // ==================================================
  // RECENT PREDICTIONS
  // ==================================================

  const [recent, setRecent] =
    useState([]);

  const [recentLoading, setRecentLoading] =
    useState(true);


  // ==================================================
  // REFS
  // ==================================================

  const startContainerRef =
    useRef(null);

  const endContainerRef =
    useRef(null);

  const endInputRef =
    useRef(null);


  // Set when the voice assistant fills a field, so the type-ahead dropdown
  // doesn't pop open for a value that was already decided.
  const skipStartSearchRef =
    useRef(false);

  const skipEndSearchRef =
    useRef(false);


  // ==================================================
  // VOICE
  // ==================================================

  const [pendingVoiceRun, setPendingVoiceRun] =
    useState(false);


  // ==================================================
  // LOAD RECENT PREDICTIONS
  // ==================================================

  useEffect(() => {

    loadRecentPredictions();

  }, []);


  // ==================================================
  // CLICK OUTSIDE
  // ==================================================

  useEffect(() => {

    function handleClickOutside(event) {

      // If click is outside Start location box
      if (
        startContainerRef.current &&
        !startContainerRef.current.contains(
          event.target
        )
      ) {
        setStartLocations([]);
      }


      // If click is outside End location box
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


  // ==================================================
  // START LOCATION GEOCODING
  // ==================================================

  useEffect(() => {

    if (skipStartSearchRef.current) {

      skipStartSearchRef.current = false;

      setStartLocations([]);

      return undefined;

    }


    const searchStartLocation =
      async () => {

        const query =
          startSearch.trim();


        if (query.length < 2) {

          setStartLocations([]);

          return;

        }


        try {

          setStartSearching(true);

          setRoadsError('');


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
            'Could not search starting location:',
            err
          );


          setStartLocations([]);


          setRoadsError(
            'Could not search locations using the geocoding service.'
          );

        } finally {

          setStartSearching(false);

        }

      };


    const timer =
      setTimeout(
        searchStartLocation,
        400
      );


    return () =>
      clearTimeout(timer);

  }, [startSearch]);


  // ==================================================
  // END LOCATION GEOCODING
  // ==================================================

  useEffect(() => {

    if (skipEndSearchRef.current) {

      skipEndSearchRef.current = false;

      setEndLocations([]);

      return undefined;

    }


    const searchEndLocation =
      async () => {

        const query =
          endSearch.trim();


        if (query.length < 2) {

          setEndLocations([]);

          return;

        }


        try {

          setEndSearching(true);

          setRoadsError('');


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
            'Could not search destination:',
            err
          );


          setEndLocations([]);


          setRoadsError(
            'Could not search locations using the geocoding service.'
          );

        } finally {

          setEndSearching(false);

        }

      };


    const timer =
      setTimeout(
        searchEndLocation,
        400
      );


    return () =>
      clearTimeout(timer);

  }, [endSearch]);


  // ==================================================
  // LOAD RECENT PREDICTIONS
  // ==================================================

  async function loadRecentPredictions() {

    setRecentLoading(true);


    try {

      const data =
        await getLatestAccidentPredictions();


      setRecent(
        Array.isArray(data)
          ? data
          : []
      );

    } catch (err) {

      console.error(
        'Could not load recent accident predictions:',
        err
      );


      setRecent([]);

    } finally {

      setRecentLoading(false);

    }

  }


  // ==================================================
  // UPDATE FORM
  // ==================================================

  function update(field, value) {

    setForm((previous) => ({

      ...previous,

      [field]: value,

    }));

  }


  // ==================================================
  // SELECT START LOCATION
  // ==================================================

  function selectStartLocation(location) {

    const locationName =
      location.display_name ||
      location.name ||
      '';


    // Put selected location into form
    update(
      'start_location',
      locationName
    );


    // Put selected location into input
    setStartSearch(
      locationName
    );


    // Close Start suggestions
    setStartLocations([]);


    /*
     * IMPORTANT:
     *
     * After selecting the Start Location,
     * automatically move the user to the
     * Destination field.
     */

    setTimeout(() => {

      endInputRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });


      endInputRef.current?.focus();

    }, 150);

  }


  // ==================================================
  // SELECT END LOCATION
  // ==================================================

  function selectEndLocation(location) {

    const locationName =
      location.display_name ||
      location.name ||
      '';


    update(
      'end_location',
      locationName
    );


    setEndSearch(
      locationName
    );


    // Close End suggestions
    setEndLocations([]);

  }


  // ==================================================
  // VOICE ASSISTANT
  // ==================================================

  function handleVoiceRoute(voice) {

    const nextStart =
      voice.start_location || '';

    const nextEnd =
      voice.end_location || '';


    if (
      nextStart &&
      nextStart !== startSearch
    ) {
      skipStartSearchRef.current = true;
    }

    if (
      nextEnd &&
      nextEnd !== endSearch
    ) {
      skipEndSearchRef.current = true;
    }


    setError('');

    setResult(null);

    setStartLocations([]);

    setEndLocations([]);


    if (nextStart) {
      setStartSearch(nextStart);
    }

    if (nextEnd) {
      setEndSearch(nextEnd);
    }


    setForm((previous) => ({

      ...previous,

      start_location:
        nextStart || previous.start_location,

      end_location:
        nextEnd || previous.end_location,

    }));


    // Both places understood -> run the prediction hands-free.
    if (voice.success) {
      setPendingVoiceRun(true);
    }

  }


  useEffect(() => {

    if (!pendingVoiceRun) return;

    setPendingVoiceRun(false);

    handleSubmit();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingVoiceRun]);


  // ==================================================
  // SUBMIT PREDICTION
  // ==================================================

  async function handleSubmit(event) {

    event?.preventDefault?.();


    setError('');

    setResult(null);


    const start =
      form.start_location.trim();

    const end =
      form.end_location.trim();


    if (!start || !end) {

      setError(
        'Please enter both the starting point and destination.'
      );

      return;

    }


    if (
      start.toLowerCase() ===
      end.toLowerCase()
    ) {

      setError(
        'Starting point and destination must be different.'
      );

      return;

    }


    setIsSubmitting(true);


    try {

      /*
       * Keep the existing accident
       * prediction backend exactly the same.
       */

      const payload = {

        start_location:
          start,

        end_location:
          end,

        persist: true,

      };


      const data =
        await predictRouteAccident(
          payload
        );


      setResult({

        ...data,

        from_road_name:
          data.start_location ||
          start,

        to_road_name:
          data.end_location ||
          end,

      });


      await loadRecentPredictions();

    } catch (err) {

      console.error(
        'Accident prediction error:',
        err
      );


      if (
        err.response?.status === 404
      ) {

        setError(
          err.response.data?.detail ||
          'The selected route could not be found.'
        );

      } else if (
        err.response?.status === 422
      ) {

        const detail =
          err.response.data?.detail;


        setError(

          Array.isArray(detail)

            ? detail
                .map(
                  (item) => item.msg
                )
                .join(', ')

            : 'Please enter valid locations.'

        );

      } else if (err.request) {

        setError(
          'Unable to connect to the Accident Prediction service.'
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


  // ==================================================
  // STYLES
  // ==================================================

  const inputClass =
    'mt-1 w-full rounded-md border border-slate-300 dark:border-asphalt-600 bg-slate-100 dark:bg-asphalt-800 px-3 py-2 text-sm text-slate-900 dark:text-asphalt-100 outline-none focus:border-signal-blue';

  const labelClass =
    'block text-xs text-slate-500 dark:text-asphalt-400';


  // ==================================================
  // UI
  // ==================================================

  return (

    <div className="space-y-6">


      {/* ==================================================
          HEADER
      ================================================== */}

      <div>

        <h1 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">

          Accident Prediction

        </h1>


        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">

          Enter a starting point and destination.
          RoadSense AI retrieves road, weather,
          traffic, and accident-history data from
          the backend to predict route risk.

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


          {/* ==================================================
              VOICE ASSISTANT
          ================================================== */}

          <VoiceAssistant
            onRoute={handleVoiceRoute}
            disabled={isSubmitting}
            hint="Try: “Accident risk from Banjara Hills to Hitec City”"
          />


          {/* ==================================================
              START LOCATION
          ================================================== */}

          <label
            className={labelClass}
            htmlFor="start_location"
          >
            Starting Point *
          </label>


          <div
            ref={startContainerRef}
            className="relative"
          >

            <input
              id="start_location"
              required
              value={startSearch}
              onChange={(event) => {

                const value =
                  event.target.value;


                setStartSearch(value);


                update(
                  'start_location',
                  value
                );

              }}
              placeholder="Search starting point..."
              className={inputClass}
              autoComplete="off"
            />


            {startSearching && (

              <span className="absolute right-3 top-3 text-xs text-slate-400">

                Searching...

              </span>

            )}


            {/* START SUGGESTIONS */}

            {startLocations.length > 0 && (

              <div className="absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900">

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


          {/* ==================================================
              END LOCATION
          ================================================== */}

          <label
            className={`${labelClass} mt-4`}
            htmlFor="end_location"
          >
            Destination *
          </label>


          <div
            ref={endContainerRef}
            className="relative"
          >

            <input
              ref={endInputRef}
              id="end_location"
              required
              value={endSearch}
              onChange={(event) => {

                const value =
                  event.target.value;


                setEndSearch(value);


                update(
                  'end_location',
                  value
                );

              }}
              placeholder="Search destination..."
              className={inputClass}
              autoComplete="off"
            />


            {endSearching && (

              <span className="absolute right-3 top-3 text-xs text-slate-400">

                Searching...

              </span>

            )}


            {/* END SUGGESTIONS */}

            {endLocations.length > 0 && (

              <div className="absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900">

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


          {/* GEOCODING ERROR */}

          {roadsError && (

            <p className="mt-2 text-xs text-slate-400 dark:text-asphalt-500">

              {roadsError}

            </p>

          )}


          {/* ERROR */}

          {error && (

            <p className="mt-4 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">

              {error}

            </p>

          )}


          {/* SUBMIT */}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 w-full rounded-md bg-signal-blue py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >

            {isSubmitting
              ? 'Predicting…'
              : 'Predict Accident Risk'}

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

              Enter your route and run a prediction
              to see the result.

            </p>

          )}


          {isSubmitting && (

            <p className="mt-4 text-sm text-slate-500 dark:text-asphalt-400">

              Analyzing road, traffic, weather,
              and accident-history data…

            </p>

          )}


          {result && !isSubmitting && (

            <div className="mt-4 space-y-4">


              {/* RISK LEVEL */}

              <div className="flex items-center gap-3">

                <RiskBadge
                  level={
                    result.risk_level ||
                    result.accident_risk_level
                  }
                />


                <span className="text-sm text-slate-600 dark:text-asphalt-300">

                  {result.road_name ||
                    'Selected route'}

                </span>

              </div>


              {/* RISK PERCENTAGE */}

              <div className="rounded-md border border-slate-200 dark:border-asphalt-700 bg-slate-50 dark:bg-asphalt-950/50 p-4">

                <p className="text-xs text-slate-500 dark:text-asphalt-400">

                  Predicted accident risk

                </p>


                <p className="mt-1 text-3xl font-semibold text-slate-900 dark:text-asphalt-100">

                  {Number(
                    result.risk_percentage ??
                    result.accident_risk ??
                    0
                  ).toFixed(1)}%

                </p>

              </div>


              {/* DETAILS */}

              <div className="grid grid-cols-2 gap-3 text-sm">


                {/* ROUTE */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Route

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {(
                      result.from_road_name ||
                      result.start_location ||
                      form.start_location
                    ).trim() ||
                      'Unknown location'}

                    {' → '}

                    {(
                      result.to_road_name ||
                      result.end_location ||
                      form.end_location
                    ).trim() ||
                      'Unknown destination'}

                  </p>

                </div>


                {/* DISTANCE */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Distance

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.distance_km != null

                      ? `${Number(
                          result.distance_km
                        ).toFixed(1)} km`

                      : '—'}

                  </p>

                </div>


                {/* CONFIDENCE */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Confidence

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.confidence_score != null

                      ? `${Number(
                          result.confidence_score
                        ).toFixed(1)}%`

                      : '—'}

                  </p>

                </div>


                {/* HISTORICAL ACCIDENTS */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Historical accidents

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.historical_accidents_count ??
                      '—'}

                  </p>

                </div>


                {/* WEATHER */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Weather

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.weather_conditions?.condition ||

                      result.weather_conditions
                        ?.weather_condition ||

                      '—'}

                  </p>

                </div>


                {/* PREDICTION TIME */}

                <div>

                  <p className="text-xs text-slate-500 dark:text-asphalt-400">

                    Prediction time

                  </p>


                  <p className="text-slate-900 dark:text-asphalt-100">

                    {result.prediction_time

                      ? new Date(
                          result.prediction_time
                        ).toLocaleString()

                      : '—'}

                  </p>

                </div>

              </div>


              {/* SAFETY RECOMMENDATION */}

              <div className="rounded-md border border-signal-blue/30 bg-signal-blue/10 p-3">

                <p className="text-xs font-medium text-signal-blue">

                  Safety Recommendation

                </p>


                <p className="mt-1 text-sm text-slate-800 dark:text-asphalt-200">

                  {['HIGH', 'CRITICAL'].includes(
                    (
                      result.risk_level ||
                      ''
                    ).toUpperCase()
                  )

                    ? 'Drive carefully, reduce speed, keep a safe distance, and consider an alternative route.'

                    : 'Follow normal road-safety practices and stay alert while driving.'}

                </p>

              </div>

            </div>

          )}

        </div>

      </div>


      {/* ==================================================
          LATEST ACCIDENT PREDICTIONS
      ================================================== */}

      <div>

        <p className="mb-2 text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">

          Latest Accident Predictions

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
                key: 'risk_level',
                header: 'Risk Level',

                render: (row) => (

                  <RiskBadge
                    level={row.risk_level}
                  />

                ),

              },


              {
                key: 'risk_percentage',
                header: 'Risk',

                render: (row) =>

                  row.risk_percentage != null

                    ? `${Number(
                        row.risk_percentage
                      ).toFixed(1)}%`

                    : '—',

              },


              {
                key: 'confidence_score',
                header: 'Confidence',

                render: (row) =>

                  row.confidence_score != null

                    ? `${Number(
                        row.confidence_score
                      ).toFixed(1)}%`

                    : '—',

              },


              {
                key: 'prediction_time',
                header: 'Predicted At',

                render: (row) =>

                  row.prediction_time

                    ? new Date(
                        row.prediction_time
                      ).toLocaleString()

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