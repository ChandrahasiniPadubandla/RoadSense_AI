import React, { useEffect, useMemo, useState } from 'react';
import { Activity, Loader2, RefreshCw, Search } from 'lucide-react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { RISK_LEVEL_COLOR } from '../utils/constants';
import {
  checkHotspotRoute,
  geocodeSearch,
  getHotspots,
  predictHotspots,
} from '../api_services';

const emptyLocationFilter = { start_location: '', end_location: '' };
const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';
const buttonClass =
  'inline-flex items-center justify-center gap-2 rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-signal-blue/90 disabled:cursor-not-allowed disabled:opacity-60';

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(', ') || fallback;
  }
  return error?.message || fallback;
}

function LocationAutocomplete({
  id,
  label,
  value,
  onChange,
  onSelect,
  placeholder,
  required = false,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchEnabled, setSearchEnabled] = useState(false);

  useEffect(() => {
    const query = value.trim();
    if (!searchEnabled || query.length < 2) {
      setSuggestions([]);
      setIsSearching(false);
      return undefined;
    }

    let active = true;
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await geocodeSearch(query, 'Hyderabad', 5);
        if (active) setSuggestions(results);
      } finally {
        if (active) setIsSearching(false);
      }
    }, 350);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [value, searchEnabled]);

  function handleChange(event) {
    setSearchEnabled(true);
    setSuggestions([]);
    onSelect?.(null);
    onChange(event.target.value);
  }

  function handleSelect(location) {
    setSearchEnabled(false);
    onChange(location.primary_name || location.display_name);
    onSelect?.(location);
    setSuggestions([]);
  }

  const listId = `${id}-suggestions`;

  return (
    <label htmlFor={id} className="text-xs font-medium text-slate-600 dark:text-asphalt-300">
      {label}
      <div className="relative mt-1">
        <input
          id={id}
          className={inputClass}
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          required={required}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={suggestions.length > 0}
          aria-controls={listId}
        />
        {isSearching && (
          <span className="absolute right-3 top-2.5 text-xs text-slate-400" aria-live="polite">
            Searching…
          </span>
        )}
        {suggestions.length > 0 && (
          <div
            id={listId}
            role="listbox"
            className="absolute left-0 right-0 z-50 mt-1 max-h-60 overflow-auto rounded-md border border-slate-200 bg-white shadow-lg dark:border-asphalt-700 dark:bg-asphalt-900"
          >
            {suggestions.map((location, index) => {
              const primaryName = location.primary_name || location.display_name;
              return (
                <button
                  key={`${location.latitude}-${location.longitude}-${index}`}
                  type="button"
                  role="option"
                  aria-selected="false"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleSelect(location)}
                  className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-slate-50 dark:border-asphalt-800 dark:hover:bg-asphalt-800"
                >
                  <span className="block font-medium text-slate-900 dark:text-asphalt-100">
                    {primaryName}
                  </span>
                  {location.display_name && location.display_name !== primaryName && (
                    <span className="mt-0.5 block text-xs text-slate-500 dark:text-asphalt-400">
                      {location.display_name}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </label>
  );
}

export default function HotspotsPage() {
  const [hotspots, setHotspots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [locationFilter, setLocationFilter] = useState(emptyLocationFilter);
  const [appliedLocationFilter, setAppliedLocationFilter] = useState(emptyLocationFilter);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [routeForm, setRouteForm] = useState(emptyLocationFilter);
  const [routeLocations, setRouteLocations] = useState({ start: null, end: null });
  const [routeResult, setRouteResult] = useState(null);
  const [routeError, setRouteError] = useState('');
  const [isCheckingRoute, setIsCheckingRoute] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadHotspots() {
      try {
        setIsLoading(true);
        setLoadError('');
        const data = await getHotspots(100, appliedLocationFilter);
        if (active) setHotspots(data);
      } catch (error) {
        console.error('Failed to load accident hotspots:', error);
        if (active) {
          setHotspots([]);
          setLoadError(getErrorMessage(error, 'Could not load accident hotspots.'));
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    loadHotspots();
    return () => {
      active = false;
    };
  }, [appliedLocationFilter, refreshKey]);

  const levels = useMemo(() => {
    const set = new Set(hotspots.map((h) => (h.risk_level || 'LOW').toUpperCase()));
    return Array.from(set);
  }, [hotspots]);

  const filteredHotspots = useMemo(() => {
    if (activeFilter === 'ALL') return hotspots;
    return hotspots.filter((h) => (h.risk_level || 'LOW').toUpperCase() === activeFilter);
  }, [hotspots, activeFilter]);

  async function handleRouteCheck(event) {
    event.preventDefault();
    setIsCheckingRoute(true);
    setRouteError('');
    setRouteResult(null);

    try {
      const result = await checkHotspotRoute({
        start_location: routeForm.start_location.trim(),
        end_location: routeForm.end_location.trim(),
        start_latitude: routeLocations.start?.latitude,
        start_longitude: routeLocations.start?.longitude,
        end_latitude: routeLocations.end?.latitude,
        end_longitude: routeLocations.end?.longitude,
      });
      setRouteResult(result);
    } catch (error) {
      console.error('Failed to check route hotspot:', error);
      setRouteError(getErrorMessage(error, 'Could not check this route.'));
    } finally {
      setIsCheckingRoute(false);
    }
  }

  async function handleRecalculate() {
    setIsRecalculating(true);
    setLoadError('');
    setSuccessMessage('');

    try {
      const result = await predictHotspots({ top_n: 15 });
      const count = Array.isArray(result?.hotspots) ? result.hotspots.length : 0;
      setSuccessMessage(
        `Hotspot analysis completed: ${count} results (${result?.model_status || 'status unavailable'}).`
      );
      setRefreshKey((current) => current + 1);
    } catch (error) {
      console.error('Failed to recalculate accident hotspots:', error);
      setLoadError(getErrorMessage(error, 'Could not recalculate accident hotspots.'));
    } finally {
      setIsRecalculating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <div>
          <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">
            Accident Hotspots
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
            View database-backed hotspots, check a route corridor, or run the hotspot analysis.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={buttonClass}
            onClick={() => setRefreshKey((current) => current + 1)}
            disabled={isLoading || isRecalculating}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh list
          </button>
          <button
            type="button"
            className={buttonClass}
            onClick={handleRecalculate}
            disabled={isRecalculating}
          >
            {isRecalculating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
            {isRecalculating ? 'Calculating…' : 'Recalculate hotspots'}
          </button>
        </div>
      </div>

      {loadError && (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {loadError}
        </p>
      )}
      {successMessage && (
        <p role="status" className="rounded-md border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300">
          {successMessage}
        </p>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-asphalt-700 dark:bg-asphalt-900">
        <h3 className="font-semibold text-slate-900 dark:text-asphalt-100">Check a route</h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Ask the backend whether a start-to-end corridor currently qualifies as an accident hotspot.
        </p>
        <form onSubmit={handleRouteCheck} className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <LocationAutocomplete
            id="route-start-location"
            label="Start location"
            value={routeForm.start_location}
            onChange={(value) => setRouteForm((form) => ({ ...form, start_location: value }))}
            onSelect={(location) => setRouteLocations((selected) => ({ ...selected, start: location }))}
            placeholder="Search starting point…"
            required
          />
          <LocationAutocomplete
            id="route-end-location"
            label="End location"
            value={routeForm.end_location}
            onChange={(value) => setRouteForm((form) => ({ ...form, end_location: value }))}
            onSelect={(location) => setRouteLocations((selected) => ({ ...selected, end: location }))}
            placeholder="Search destination…"
            required
          />
          <button type="submit" className={`${buttonClass} self-end`} disabled={isCheckingRoute}>
            {isCheckingRoute ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Check route
          </button>
        </form>

        {routeError && (
          <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{routeError}</p>
        )}
        {routeResult && (
          <div
            role="status"
            className={`mt-4 rounded-md border p-3 text-sm ${
              routeResult.is_hotspot
                ? 'border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300'
                : 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300'
            }`}
          >
            <p className="font-semibold">{routeResult.is_hotspot ? 'Hotspot route' : 'Not currently a hotspot'}</p>
            <p className="mt-1">{routeResult.message}</p>
            {routeResult.found && (
              <p className="mt-1">
                Risk: {routeResult.risk_level} · Accidents: {routeResult.accident_count}
                {routeResult.risk_score != null ? ` · Score: ${routeResult.risk_score}` : ''}
              </p>
            )}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-asphalt-700 dark:bg-asphalt-900">
        <h3 className="font-semibold text-slate-900 dark:text-asphalt-100">Filter hotspot list</h3>
        <form
          className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedLocationFilter({
              start_location: locationFilter.start_location.trim(),
              end_location: locationFilter.end_location.trim(),
            });
          }}
        >
          <LocationAutocomplete
            id="filter-start-location"
            label="Start location"
            value={locationFilter.start_location}
            onChange={(value) => setLocationFilter((filter) => ({ ...filter, start_location: value }))}
            placeholder="Search starting point…"
          />
          <LocationAutocomplete
            id="filter-end-location"
            label="End location"
            value={locationFilter.end_location}
            onChange={(value) => setLocationFilter((filter) => ({ ...filter, end_location: value }))}
            placeholder="Search destination…"
          />
          <button type="submit" className={`${buttonClass} self-end`}>
            <Search className="h-4 w-4" />
            Apply filters
          </button>
          <button
            type="button"
            className="self-end rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-asphalt-600 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
            onClick={() => {
              setLocationFilter(emptyLocationFilter);
              setAppliedLocationFilter(emptyLocationFilter);
            }}
          >
            Clear
          </button>
        </form>
      </section>

      {!isLoading && !loadError && (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="risk-filter" className="text-sm font-medium text-slate-600 dark:text-asphalt-300">
            Filter by risk level:
          </label>
          <select
            id="risk-filter"
            value={activeFilter}
            onChange={(event) => setActiveFilter(event.target.value)}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-200"
          >
            <option value="ALL">All</option>
            {levels.map((level) => <option key={level} value={level}>{level}</option>)}
          </select>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading hotspots…</p>
      ) : !loadError ? (
        <DataTable
          columns={[
            {
              key: 'location',
              header: 'Location / route',
              render: (hotspot) => hotspot.start_location && hotspot.end_location
                ? `${hotspot.start_location} → ${hotspot.end_location}`
                : hotspot.zone_name || 'Unnamed zone',
            },
            { key: 'accident_count', header: 'Accidents', render: (hotspot) => hotspot.accident_count ?? 0 },
            {
              key: 'risk_level',
              header: 'Risk level',
              render: (hotspot) => (
                <LevelBadge
                  level={hotspot.risk_level ? hotspot.risk_level.toUpperCase() : null}
                  colorMap={RISK_LEVEL_COLOR}
                  fallbackText="Unassessed"
                />
              ),
            },
            { key: 'risk_score', header: 'Risk score', render: (hotspot) => hotspot.risk_score ?? '—' },
            {
              key: 'coords',
              header: 'Coordinates',
              render: (hotspot) => hotspot.latitude != null && hotspot.longitude != null
                ? `${Number(hotspot.latitude).toFixed(4)}, ${Number(hotspot.longitude).toFixed(4)}`
                : '—',
            },
            {
              key: 'calculated_at',
              header: 'Last calculated',
              render: (hotspot) => hotspot.calculated_at ? new Date(hotspot.calculated_at).toLocaleString() : '—',
            },
          ]}
          rows={filteredHotspots.map((hotspot, index) => ({
            ...hotspot,
            id: hotspot.hotspot_id || `${hotspot.zone_id || 'hotspot'}-${index}`,
          }))}
          emptyMessage={
            activeFilter !== 'ALL'
              ? `No ${activeFilter.toLowerCase()} risk hotspots found.`
              : appliedLocationFilter.start_location || appliedLocationFilter.end_location
                ? 'No hotspots matched those locations.'
                : 'No accident hotspots have been calculated yet. Use “Recalculate hotspots” to run the analysis.'
          }
        />
      ) : null}
    </div>
  );
}
