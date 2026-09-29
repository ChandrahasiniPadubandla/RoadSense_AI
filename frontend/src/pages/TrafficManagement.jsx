
import React, { useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import { getTrafficRecords, geocodeSearch } from '../api_services';

const LEVEL_OPTIONS = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'SEVERE'];

export default function TrafficManagement() {
  const [records, setRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');

  // Geocoding results
  const [geoResults, setGeoResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);

  // Load traffic records only.
  // No getAllRoads() call anymore.
  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);

        const trafficData = await getTrafficRecords();

        setRecords(trafficData);
      } catch (error) {
        console.error('Failed to load traffic records:', error);
        setRecords([]);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

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

  // Filter traffic records.
  //
  // If a geocoded location is selected, compare its
  // coordinates with traffic-record coordinates when available.
  //
  // Otherwise, use the typed search text against any road-name
  // information that may already exist in the traffic record.
  const filtered = useMemo(() => {
    return records.filter((r) => {
      let matchesSearch = true;

      if (selectedLocation) {
        const selectedLat = Number(
          selectedLocation.lat ??
          selectedLocation.latitude
        );

        const selectedLng = Number(
          selectedLocation.lon ??
          selectedLocation.lng ??
          selectedLocation.longitude
        );

        const recordLat = Number(
          r.latitude ??
          r.lat ??
          r.start_latitude
        );

        const recordLng = Number(
          r.longitude ??
          r.lng ??
          r.start_longitude
        );

        if (
          Number.isFinite(selectedLat) &&
          Number.isFinite(selectedLng) &&
          Number.isFinite(recordLat) &&
          Number.isFinite(recordLng)
        ) {
          // Approximate coordinate matching.
          // 0.01 degrees is roughly around 1 km.
          const latDifference = Math.abs(recordLat - selectedLat);
          const lngDifference = Math.abs(recordLng - selectedLng);

          matchesSearch =
            latDifference <= 0.01 &&
            lngDifference <= 0.01;
        }
      } else if (search.trim()) {
        const searchText = search.toLowerCase();

        const roadName =
          r.road_name ||
          r.road ||
          r.location ||
          '';

        matchesSearch = roadName
          .toString()
          .toLowerCase()
          .includes(searchText);
      }

      const matchesLevel =
        levelFilter === 'ALL' ||
        (r.congestion_level || '').toUpperCase() === levelFilter;

      return matchesSearch && matchesLevel;
    });
  }, [records, search, selectedLocation, levelFilter]);

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
          onChange={(e) => setLevelFilter(e.target.value)}
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
      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">
          Loading traffic records…
        </p>
      ) : (
        <DataTable
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

          rows={filtered.map((r) => ({
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
