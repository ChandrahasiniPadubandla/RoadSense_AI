import React, { useEffect, useRef, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import { getTrafficRecordsPage, geocodeSearch } from '../api_services';

const LEVEL_OPTIONS = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'SEVERE'];

export default function TrafficManagement() {
  // Server-side pagination state: `records` only ever holds the CURRENT page.
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');

  // Geocoding results
  const [geoResults, setGeoResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);

  const requestId = useRef(0);
  const lastApplied = useRef('');

  // Debounce the road-name search that is sent to the backend.
  // A picked geocoded place is a place label rather than a road name, so it is
  // not sent as a road-name filter (same behaviour as before pagination).
  useEffect(() => {
    const timer = setTimeout(() => {
      const next = selectedLocation ? '' : search.trim();
      if (next !== lastApplied.current) {
        lastApplied.current = next;
        setAppliedSearch(next);
        setPage(1);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [search, selectedLocation]);

  // Load ONE page of traffic records from the backend
  // (filters + OFFSET/LIMIT are applied in SQL, total comes from X-Total-Count).
  useEffect(() => {
    const current = ++requestId.current;
    (async () => {
      try {
        setIsLoading(true);
        setLoadError('');

        const result = await getTrafficRecordsPage({
          page,
          pageSize,
          level: levelFilter,
          search: appliedSearch,
        });

        if (current !== requestId.current) return; // a newer request superseded this one
        setRecords(result.items);
        setTotal(result.total);
      } catch (error) {
        if (current !== requestId.current) return;
        console.error('Failed to load traffic records:', error);
        setRecords([]);
        setTotal(0);
        setLoadError('Could not load traffic records from the server.');
      } finally {
        if (current === requestId.current) setIsLoading(false);
      }
    })();
  }, [page, pageSize, levelFilter, appliedSearch]);

  // Search locations using the existing
  // OpenStreetMap Nominatim geocoding API.
  useEffect(() => {
    const searchLocation = async () => {
      const query = search.trim();

      if (query.length < 2) {
        setGeoResults([]);
        return;
      }

      try {
        setIsSearching(true);

        const results = await geocodeSearch(query, 'Hyderabad', 5);

        setGeoResults(Array.isArray(results) ? results : []);
      } catch (error) {
        console.error('Geocoding search failed:', error);
        setGeoResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    const timer = setTimeout(searchLocation, 400);

    return () => clearTimeout(timer);
  }, [search]);


  const inputClass =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';

  function handleLocationSelect(location) {
    setSelectedLocation(location);

    // Display the selected place name in the input.
    setSearch(
      location.display_name ||
      location.name ||
      ''
    );

    setGeoResults([]);
  }

  function clearLocationSearch() {
    setSearch('');
    setSelectedLocation(null);
    setGeoResults([]);
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">
          Traffic Management
        </h2>

        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Real recorded traffic observations from the database — vehicle counts,
          speeds, congestion levels, and conditions.
        </p>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-wrap gap-2">

        <div className="relative">

          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedLocation(null);
            }}
            placeholder="Search road or location…"
            className={`${inputClass} w-80`}
          />

          {/* Loading indicator */}
          {isSearching && (
            <div className="absolute right-3 top-2.5 text-xs text-slate-400">
              Searching…
            </div>
          )}

          {/* Geocoding suggestions */}
          {geoResults.length > 0 && !selectedLocation && (
            <div className="absolute left-0 right-0 z-50 mt-1 max-h-64 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900">

              {geoResults.map((location, index) => (
                <button
                  key={`${location.place_id || index}`}
                  type="button"
                  onClick={() => handleLocationSelect(location)}
                  className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-slate-50 dark:border-asphalt-800 dark:hover:bg-asphalt-800"
                >
                  <div className="font-medium text-slate-900 dark:text-white">
                    {location.name || location.display_name}
                  </div>

                  {location.display_name && (
                    <div className="mt-0.5 text-xs text-slate-500 dark:text-asphalt-400">
                      {location.display_name}
                    </div>
                  )}
                </button>
              ))}

            </div>
          )}

        </div>

        {/* Clear button */}
        {search && (
          <button
            type="button"
            onClick={clearLocationSearch}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
          >
            Clear
          </button>
        )}

        {/* Congestion filter */}
        <select
          value={levelFilter}
          onChange={(e) => {
            setLevelFilter(e.target.value);
            setPage(1);
          }}
          className={inputClass}
        >
          {LEVEL_OPTIONS.map((lvl) => (
            <option key={lvl} value={lvl}>
              {lvl === 'ALL'
                ? 'All congestion levels'
                : lvl}
            </option>
          ))}
        </select>

      </div>

      {/* Selected location */}
      {selectedLocation && (
        <div className="rounded-md border border-signal-blue/30 bg-signal-blue/5 px-4 py-3 text-sm">

          <div className="font-medium text-slate-900 dark:text-white">
            Selected location
          </div>

          <div className="mt-1 text-xs text-slate-500 dark:text-asphalt-400">
            {selectedLocation.display_name ||
              selectedLocation.name}
          </div>

          {(selectedLocation.lat ||
            selectedLocation.latitude) && (
            <div className="mt-1 text-xs text-slate-400">
              Coordinates:{' '}
              {selectedLocation.lat ||
                selectedLocation.latitude}
              ,{' '}
              {selectedLocation.lon ||
                selectedLocation.lng ||
                selectedLocation.longitude}
            </div>
          )}

        </div>
      )}

      {/* Table */}
      {loadError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {loadError}
        </div>
      )}

      {isLoading && records.length === 0 && !loadError ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">
          Loading traffic records…
        </p>
      ) : (
        <DataTable
          pagination={{
            page,
            pageSize,
            total,
            loading: isLoading,
            onPageChange: setPage,
            onPageSizeChange: (size) => {
              setPageSize(size);
              setPage(1);
            },
          }}
          label="traffic records"
          columns={[
            {
              key: 'road',
              header: 'Road',
              render: (r) =>
                r.road_name ||
                r.road ||
                r.location ||
                r.road_id ||
                '—',
            },

            {
              key: 'timestamp',
              header: 'Recorded',
              render: (r) =>
                r.timestamp
                  ? new Date(r.timestamp).toLocaleString()
                  : '—',
            },

            {
              key: 'vehicle_count',
              header: 'Vehicles',
            },

            {
              key: 'average_speed',
              header: 'Avg speed',
              render: (r) =>
                r.average_speed != null
                  ? `${r.average_speed} km/h`
                  : '—',
            },

            {
              key: 'congestion_level',
              header: 'Congestion',
              render: (r) => (
                <LevelBadge
                  level={(r.congestion_level || 'LOW').toUpperCase()}
                  colorMap={TRAFFIC_LEVEL_COLOR}
                />
              ),
            },

            {
              key: 'weather_condition',
              header: 'Weather',
              render: (r) =>
                r.weather_condition || '—',
            },
          ]}

          rows={records.map((r) => ({
            ...r,
            id: r.traffic_id,
          }))}

          emptyMessage={
            search
              ? 'No traffic records found for this location.'
              : 'No traffic records found in the database for this filter.'
          }
        />
      )}

    </div>
  );
}
