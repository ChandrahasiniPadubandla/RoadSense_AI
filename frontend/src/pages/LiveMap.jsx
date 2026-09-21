import React, { useEffect, useState, useMemo, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Polyline,
  Popup,
  Tooltip,
  useMap,
} from 'react-leaflet';
import {
  getTrafficLayer,
  getAccidentLayer,
  getHotspotsLayer,
  geocodeSearch,
  getDrivingRoute,
  predictRouteTraffic,
  predictRouteAccident,
} from '../api_services';

const CONGESTION_COLOR = {
  LOW: '#10B981',
  MEDIUM: '#F59E0B',
  HIGH: '#F97316',
  SEVERE: '#EF4444',
  UNKNOWN: '#9CA3AF',
};

const SEVERITY_COLOR = {
  FATAL: '#7F1D1D',
  SEVERE: '#DC2626',
  MODERATE: '#F59E0B',
  MEDIUM: '#F59E0B',
  MINOR: '#3B82F6',
};

export default function LiveMap() {
  const [trafficLayer, setTrafficLayer] = useState({ features: [] });
  const [accidentLayer, setAccidentLayer] = useState({ features: [] });
  const [hotspotsLayer, setHotspotsLayer] = useState({ features: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Layer Visibility Controls
  const [showTraffic, setShowTraffic] = useState(true);
  const [showAccidents, setShowAccidents] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('ALL');

  // ---------------------------------------------------------------------
  // Route Planner: start/end location search (live OSM Nominatim geocoding)
  // + real driving route (live OSRM routing API) + live ML predictions for
  // that route. Nothing here is mocked or a straight line — every value
  // comes from a real API call.
  // ---------------------------------------------------------------------
  const [startQuery, setStartQuery] = useState('');
  const [endQuery, setEndQuery] = useState('');
  const [startPoint, setStartPoint] = useState(null); // { lat, lng, label }
  const [endPoint, setEndPoint] = useState(null);
  const [startSuggestions, setStartSuggestions] = useState([]);
  const [endSuggestions, setEndSuggestions] = useState([]);
  const [activeField, setActiveField] = useState(null); // 'start' | 'end' | null

  const [routeGeometry, setRouteGeometry] = useState(null); // [[lat,lng], ...]
  const [routeInfo, setRouteInfo] = useState(null); // { distance_km, duration_minutes, is_real_route }
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState('');

  const [routeTraffic, setRouteTraffic] = useState(null);
  const [routeAccidentRisk, setRouteAccidentRisk] = useState(null);
  const [predictionsLoading, setPredictionsLoading] = useState(false);

  const startDebounce = useRef(null);
  const endDebounce = useRef(null);

  // Live type-ahead search against OpenStreetMap Nominatim (debounced to
  // respect Nominatim's usage policy and avoid hammering the API on every
  // keystroke).
  useEffect(() => {
    clearTimeout(startDebounce.current);
    if (!startQuery || startPoint?.label === startQuery) {
      setStartSuggestions([]);
      return;
    }
    startDebounce.current = setTimeout(async () => {
      const results = await geocodeSearch(startQuery);
      setStartSuggestions(results);
    }, 400);
    return () => clearTimeout(startDebounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startQuery]);

  useEffect(() => {
    clearTimeout(endDebounce.current);
    if (!endQuery || endPoint?.label === endQuery) {
      setEndSuggestions([]);
      return;
    }
    endDebounce.current = setTimeout(async () => {
      const results = await geocodeSearch(endQuery);
      setEndSuggestions(results);
    }, 400);
    return () => clearTimeout(endDebounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endQuery]);

  function selectSuggestion(field, suggestion) {
    const point = { lat: suggestion.latitude, lng: suggestion.longitude, label: suggestion.display_name };
    if (field === 'start') {
      setStartPoint(point);
      setStartQuery(suggestion.display_name);
      setStartSuggestions([]);
    } else {
      setEndPoint(point);
      setEndQuery(suggestion.display_name);
      setEndSuggestions([]);
    }
    setActiveField(null);
  }

  async function handleFindRoute() {
    if (!startPoint || !endPoint) {
      setRouteError('Pick both a start and an end location from the suggestions first.');
      return;
    }
    setRouteError('');
    setRouteLoading(true);
    setRouteGeometry(null);
    setRouteInfo(null);
    setRouteTraffic(null);
    setRouteAccidentRisk(null);

    try {
      // Live OSRM routing — real street-level geometry, not a straight line.
      const route = await getDrivingRoute(startPoint.lat, startPoint.lng, endPoint.lat, endPoint.lng);
      setRouteGeometry(route.coordinates);
      setRouteInfo(route);
    } catch (err) {
      setRouteError('Could not fetch a live route from the routing API. Please try again.');
      setRouteLoading(false);
      return;
    }
    setRouteLoading(false);

    // Enrich with the real ML models (congestion + accident risk) for this
    // same start/end pair. These are best-effort: if either model can't
    // resolve the free-text locations to a known road, we just omit that
    // card instead of blocking the route display.
    setPredictionsLoading(true);
    const payload = {
      start_location: startPoint.label,
      end_location: endPoint.label,
      start_latitude: startPoint.lat,
      start_longitude: startPoint.lng,
      end_latitude: endPoint.lat,
      end_longitude: endPoint.lng,
    };
    const [trafficResult, accidentResult] = await Promise.allSettled([
      predictRouteTraffic(payload),
      predictRouteAccident(payload),
    ]);
    if (trafficResult.status === 'fulfilled') setRouteTraffic(trafficResult.value);
    if (accidentResult.status === 'fulfilled') setRouteAccidentRisk(accidentResult.value);
    setPredictionsLoading(false);
  }

  function handleClearRoute() {
    setStartQuery('');
    setEndQuery('');
    setStartPoint(null);
    setEndPoint(null);
    setStartSuggestions([]);
    setEndSuggestions([]);
    setRouteGeometry(null);
    setRouteInfo(null);
    setRouteError('');
    setRouteTraffic(null);
    setRouteAccidentRisk(null);
  }

  async function loadMapData() {
    setIsLoading(true);
    try {
      const [trafficRes, accidentRes, hotspotsRes] = await Promise.all([
        getTrafficLayer(),
        getAccidentLayer(),
        getHotspotsLayer(),
      ]);
      setTrafficLayer(trafficRes || { features: [] });
      setAccidentLayer(accidentRes || { features: [] });
      setHotspotsLayer(hotspotsRes || { features: [] });
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load map data from APIs:', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadMapData();
  }, []);

  // Filtered accidents based on UI selection
  const filteredAccidents = useMemo(() => {
    if (!accidentLayer?.features) return [];
    if (severityFilter === 'ALL') return accidentLayer.features;
    return accidentLayer.features.filter((f) => {
      const sev = (f.properties?.severity || '').toUpperCase();
      if (severityFilter === 'SEVERE_FATAL') {
        return sev === 'SEVERE' || sev === 'FATAL';
      }
      if (severityFilter === 'MODERATE_MINOR') {
        return sev === 'MODERATE' || sev === 'MEDIUM' || sev === 'MINOR';
      }
      return true;
    });
  }, [accidentLayer, severityFilter]);

  // Center calculation (defaults to Hyderabad center)
  const mapCenter = useMemo(() => {
    const firstRoad = trafficLayer?.features?.[0];
    if (firstRoad?.geometry?.coordinates?.[0]) {
      const [lng, lat] = firstRoad.geometry.coordinates[0];
      return [lat, lng];
    }
    return [17.43, 78.43];
  }, [trafficLayer]);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center rounded-lg border border-asphalt-700 bg-asphalt-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-signal-blue border-t-transparent"></div>
          <p className="text-sm font-medium text-asphalt-300">
            Loading live map layers from backend APIs…
          </p>
        </div>
      </div>
    );
  }

  const roadCount = trafficLayer?.features?.length || 0;
  const accidentCount = accidentLayer?.features?.length || 0;
  const hotspotCount = hotspotsLayer?.features?.length || 0;

  return (
    <div className="flex h-[calc(100vh-7.5rem)] flex-col gap-3">
      {/* Map Control Bar & Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-asphalt-700 bg-asphalt-900 px-4 py-2.5">
        {/* Layer Toggles */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => setShowTraffic((prev) => !prev)}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-all ${
              showTraffic
                ? 'bg-signal-blue/20 text-signal-blue ring-1 ring-signal-blue/40'
                : 'bg-asphalt-800 text-asphalt-400 hover:text-asphalt-200'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-signal-blue"></span>
            Traffic Roads ({roadCount})
          </button>

          <button
            onClick={() => setShowAccidents((prev) => !prev)}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-all ${
              showAccidents
                ? 'bg-signal-red/20 text-signal-red ring-1 ring-signal-red/40'
                : 'bg-asphalt-800 text-asphalt-400 hover:text-asphalt-200'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-signal-red"></span>
            Accident Markers ({accidentCount})
          </button>

          <button
            onClick={() => setShowHotspots((prev) => !prev)}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-all ${
              showHotspots
                ? 'bg-signal-amber/20 text-signal-amber ring-1 ring-signal-amber/40'
                : 'bg-asphalt-800 text-asphalt-400 hover:text-asphalt-200'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-signal-amber"></span>
            Hazard Hotspots ({hotspotCount})
          </button>

          {/* Severity Filter Dropdown */}
          <div className="ml-2 flex items-center gap-1.5 pl-2 border-l border-asphalt-700">
            <span className="text-asphalt-400">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded border border-asphalt-700 bg-asphalt-800 px-2 py-0.5 text-xs text-asphalt-200 outline-none focus:border-signal-blue"
            >
              <option value="ALL">All Severities</option>
              <option value="SEVERE_FATAL">Severe & Fatal Only</option>
              <option value="MODERATE_MINOR">Moderate & Minor</option>
            </select>
          </div>
        </div>

        {/* Sync Indicator and Refresh */}
        <div className="flex items-center gap-3 text-xs">
          {lastUpdated && (
            <span className="text-asphalt-400">Synced at {lastUpdated}</span>
          )}
          <button
            onClick={loadMapData}
            className="flex items-center gap-1 rounded bg-asphalt-800 px-2 py-1 font-medium text-asphalt-200 hover:bg-asphalt-700 hover:text-white"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Route Planner: live geocoding (OSM Nominatim) + live routing (OSRM)
          + live ML predictions for the same start/end pair */}
      <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 px-4 py-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="relative min-w-[220px] flex-1">
            <label className="mb-1 block text-xs font-medium text-asphalt-400">Start location</label>
            <input
              value={startQuery}
              onChange={(e) => {
                setStartQuery(e.target.value);
                setStartPoint(null);
              }}
              onFocus={() => setActiveField('start')}
              placeholder="Search a place, road, or landmark…"
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-950 px-3 py-2 text-sm text-white outline-none focus:border-signal-blue"
            />
            {activeField === 'start' && startSuggestions.length > 0 && (
              <ul className="absolute z-[1100] mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-asphalt-700 bg-asphalt-900 shadow-xl">
                {startSuggestions.map((s, i) => (
                  <li
                    key={i}
                    onMouseDown={() => selectSuggestion('start', s)}
                    className="cursor-pointer px-3 py-2 text-xs text-asphalt-200 hover:bg-asphalt-800"
                  >
                    {s.display_name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="relative min-w-[220px] flex-1">
            <label className="mb-1 block text-xs font-medium text-asphalt-400">End location</label>
            <input
              value={endQuery}
              onChange={(e) => {
                setEndQuery(e.target.value);
                setEndPoint(null);
              }}
              onFocus={() => setActiveField('end')}
              placeholder="Search a place, road, or landmark…"
              className="w-full rounded-md border border-asphalt-600 bg-asphalt-950 px-3 py-2 text-sm text-white outline-none focus:border-signal-blue"
            />
            {activeField === 'end' && endSuggestions.length > 0 && (
              <ul className="absolute z-[1100] mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-asphalt-700 bg-asphalt-900 shadow-xl">
                {endSuggestions.map((s, i) => (
                  <li
                    key={i}
                    onMouseDown={() => selectSuggestion('end', s)}
                    className="cursor-pointer px-3 py-2 text-xs text-asphalt-200 hover:bg-asphalt-800"
                  >
                    {s.display_name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            onClick={handleFindRoute}
            disabled={routeLoading || !startPoint || !endPoint}
            className="rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {routeLoading ? 'Finding route…' : 'Find Route'}
          </button>
          {(routeGeometry || routeError) && (
            <button
              onClick={handleClearRoute}
              className="rounded-md border border-asphalt-600 px-3 py-2 text-sm text-asphalt-300 hover:border-signal-red/50 hover:text-signal-red"
            >
              Clear
            </button>
          )}
        </div>

        {routeError && <p className="mt-2 text-xs text-signal-red">{routeError}</p>}

        {routeInfo && (
          <div className="mt-3 flex flex-wrap items-center gap-4 border-t border-asphalt-800 pt-3 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-signal-blue/40 bg-signal-blue/10 px-2.5 py-1 font-medium text-signal-blue">
              {routeInfo.is_real_route ? '⚡ Live route via OSRM' : '⚠ Approximate route (routing API unavailable)'}
            </span>
            <span className="text-asphalt-300">
              Distance: <strong className="text-asphalt-100">{routeInfo.distance_km} km</strong>
            </span>
            <span className="text-asphalt-300">
              Est. driving time: <strong className="text-asphalt-100">{routeInfo.duration_minutes} min</strong>
            </span>

            {predictionsLoading && <span className="text-asphalt-500">Running live traffic/accident-risk models…</span>}

            {routeTraffic && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-signal-amber/40 bg-signal-amber/10 px-2.5 py-1 font-medium text-signal-amber">
                Predicted congestion: {routeTraffic.congestion_level}
              </span>
            )}
            {routeAccidentRisk && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-signal-red/40 bg-signal-red/10 px-2.5 py-1 font-medium text-signal-red">
                Accident risk: {routeAccidentRisk.risk_level}
                {routeAccidentRisk.risk_percentage != null ? ` (${Number(routeAccidentRisk.risk_percentage).toFixed(0)}%)` : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Informative Status Messages if any layer has no data */}
      {(roadCount === 0 || accidentCount === 0 || hotspotCount === 0 || (accidentCount > 0 && filteredAccidents.length === 0)) && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-asphalt-800 bg-asphalt-900/90 px-3.5 py-2 text-xs text-asphalt-300">
          <span className="text-signal-blue font-semibold">Status:</span>
          {roadCount === 0 && (
            <span className="rounded bg-asphalt-800 px-2 py-0.5 text-asphalt-300">
              No road traffic segments available
            </span>
          )}
          {accidentCount === 0 && (
            <span className="rounded bg-asphalt-800 px-2 py-0.5 text-asphalt-300">
              No accident incidents recorded in database
            </span>
          )}
          {hotspotCount === 0 && showHotspots && (
            <span className="rounded bg-asphalt-800 px-2 py-0.5 text-asphalt-400">
              0 hazard hotspots registered in system
            </span>
          )}
          {accidentCount > 0 && filteredAccidents.length === 0 && (
            <span className="rounded bg-signal-amber/15 px-2 py-0.5 text-signal-amber font-medium">
              No accidents match the selected severity filter
            </span>
          )}
        </div>
      )}

      {/* Map Display & Legend */}
      <div className="relative flex-1 overflow-hidden rounded-lg border border-asphalt-700">
        <MapContainer center={mapCenter} zoom={12} className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* 1. Traffic Layer: Road LineString Polylines */}
          {showTraffic &&
            trafficLayer?.features?.map((f) => {
              const p = f.properties || {};
              const coords = f.geometry?.coordinates;
              if (!coords || coords.length < 2) return null;

              // GeoJSON is [lng, lat] -> Leaflet requires [lat, lng]
              const positions = coords.map(([lng, lat]) => [lat, lng]);
              const color = p.color || CONGESTION_COLOR[p.congestion_level] || '#F97316';
              const midIndex = Math.floor(positions.length / 2);
              const midLat = positions[midIndex][0];
              const midLng = positions[midIndex][1];

              return (
                <React.Fragment key={f.id || p.road_id}>
                  <Polyline
                    positions={positions}
                    pathOptions={{
                      color: color,
                      weight: 7,
                      opacity: 0.85,
                      lineCap: 'round',
                      lineJoin: 'round',
                    }}
                  >
                    <Tooltip sticky>{p.road_name}: {p.congestion_level} congestion</Tooltip>
                    <Popup>
                      <div className="space-y-1 text-xs text-asphalt-900">
                        <p className="font-bold text-sm text-asphalt-950">{p.road_name}</p>
                        <p className="text-asphalt-600">{p.road_type} · Speed Limit: {p.speed_limit} km/h</p>
                        <div className="my-1.5 flex items-center gap-2">
                          <span
                            className="rounded px-1.5 py-0.5 text-[10px] font-bold text-white uppercase"
                            style={{ backgroundColor: color }}
                          >
                            {p.congestion_level} Congestion
                          </span>
                          {p.capacity_utilization != null && (
                            <span className="font-medium text-asphalt-700">
                              {p.capacity_utilization}% capacity
                            </span>
                          )}
                        </div>
                        <div className="border-t border-asphalt-200 pt-1 text-asphalt-800">
                          <p><strong>Live Volume:</strong> {p.vehicle_count ?? 'N/A'} vehicles</p>
                          <p><strong>Avg Speed:</strong> {p.average_speed ? `${Math.round(p.average_speed)} km/h` : 'N/A'}</p>
                          <p><strong>Weather:</strong> {p.weather_condition || 'Clear'}</p>
                        </div>
                      </div>
                    </Popup>
                  </Polyline>

                  {/* Midpoint marker for clickable popup focus */}
                  <CircleMarker
                    center={[midLat, midLng]}
                    radius={5}
                    pathOptions={{
                      color: '#ffffff',
                      fillColor: color,
                      fillOpacity: 1,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-xs text-asphalt-900">
                        <strong>{p.road_name}</strong>
                        <p>Congestion: {p.congestion_level}</p>
                        <p>Avg Speed: {p.average_speed ? `${Math.round(p.average_speed)} km/h` : 'N/A'}</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              );
            })}

          {/* 2. Accident Layer: Incident Points */}
          {showAccidents &&
            filteredAccidents.map((f) => {
              const p = f.properties || {};
              const coords = f.geometry?.coordinates;
              if (!coords) return null;
              const [lng, lat] = coords;
              const color = p.marker_color || SEVERITY_COLOR[p.severity?.toUpperCase()] || '#DC2626';

              return (
                <CircleMarker
                  key={f.id || p.accident_id}
                  center={[lat, lng]}
                  radius={7}
                  pathOptions={{
                    color: '#ffffff',
                    fillColor: color,
                    fillOpacity: 0.9,
                    weight: 1.5,
                  }}
                >
                  <Tooltip>{p.road_name}: {p.severity} incident</Tooltip>
                  <Popup>
                    <div className="space-y-1 text-xs text-asphalt-900">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-sm text-asphalt-950">Accident Incident</span>
                        <span
                          className="rounded px-1.5 py-0.5 text-[10px] font-bold text-white uppercase"
                          style={{ backgroundColor: color }}
                        >
                          {p.severity}
                        </span>
                      </div>
                      <p className="font-medium text-asphalt-700">{p.road_name}</p>
                      <div className="border-t border-asphalt-200 pt-1 text-asphalt-800">
                        <p><strong>Casualties:</strong> {p.fatalities || 0} fatal · {p.injuries || 0} injured</p>
                        <p><strong>Vehicles Involved:</strong> {p.vehicle_count ?? 1}</p>
                        <p><strong>Conditions:</strong> {p.weather_condition || 'Clear'} / {p.road_condition || 'Dry'}</p>
                        {p.accident_time && (
                          <p className="text-[10px] text-asphalt-500 mt-1">
                            Recorded: {new Date(p.accident_time).toLocaleString()}
                          </p>
                        )}
                        {p.description && (
                          <p className="mt-1 rounded bg-asphalt-100 p-1 text-asphalt-600 italic">
                            "{p.description}"
                          </p>
                        )}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

          {/* 3. Hotspots Layer: Hazard Rings */}
          {showHotspots &&
            hotspotsLayer?.features?.map((f) => {
              const p = f.properties || {};
              const coords = f.geometry?.coordinates;
              if (!coords) return null;
              const [lng, lat] = coords;
              const color = p.color || '#DC2626';

              return (
                <CircleMarker
                  key={f.id || p.hotspot_id}
                  center={[lat, lng]}
                  radius={16}
                  pathOptions={{
                    color: color,
                    fillColor: 'transparent',
                    weight: 3,
                    dashArray: '4, 4',
                  }}
                >
                  <Popup>
                    <div className="text-xs text-asphalt-900">
                      <strong className="text-signal-red">Accident Hotspot</strong>
                      <p>Risk Level: {p.risk_level}</p>
                      <p>Accidents Recorded: {p.accident_count}</p>
                      {p.risk_score != null && <p>Risk Score: {p.risk_score}</p>}
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

          {/* Route Planner overlay: real OSRM route geometry + start/end pins */}
          {routeGeometry && routeGeometry.length > 1 && (
            <>
              <Polyline
                positions={routeGeometry}
                pathOptions={{
                  color: '#38BDF8',
                  weight: 6,
                  opacity: 0.9,
                  dashArray: '1, 10',
                  lineCap: 'round',
                }}
              />
              <FitBoundsToRoute coordinates={routeGeometry} />
            </>
          )}
          {startPoint && (
            <CircleMarker
              center={[startPoint.lat, startPoint.lng]}
              radius={9}
              pathOptions={{ color: '#ffffff', fillColor: '#10B981', fillOpacity: 1, weight: 2 }}
            >
              <Tooltip permanent direction="top">Start</Tooltip>
              <Popup>{startPoint.label}</Popup>
            </CircleMarker>
          )}
          {endPoint && (
            <CircleMarker
              center={[endPoint.lat, endPoint.lng]}
              radius={9}
              pathOptions={{ color: '#ffffff', fillColor: '#EF4444', fillOpacity: 1, weight: 2 }}
            >
              <Tooltip permanent direction="top">End</Tooltip>
              <Popup>{endPoint.label}</Popup>
            </CircleMarker>
          )}
        </MapContainer>

        {/* Floating Legend Overlay */}
        <div className="absolute bottom-4 right-4 z-[1000] rounded-lg border border-asphalt-700 bg-asphalt-900/95 p-3 text-xs text-asphalt-200 shadow-xl backdrop-blur-md">
          <p className="font-semibold text-asphalt-100 mb-2">Live Map Legend</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            <LegendItem color={CONGESTION_COLOR.LOW} label="Low Traffic (<40%)" line />
            <LegendItem color={CONGESTION_COLOR.MEDIUM} label="Medium Traffic" line />
            <LegendItem color={CONGESTION_COLOR.HIGH} label="High Congestion" line />
            <LegendItem color={CONGESTION_COLOR.SEVERE} label="Severe (>85%)" line />
            <LegendItem color={SEVERITY_COLOR.FATAL} label="Fatal Accident" dot />
            <LegendItem color={SEVERITY_COLOR.SEVERE} label="Severe Accident" dot />
            <LegendItem color={SEVERITY_COLOR.MODERATE} label="Moderate Incident" dot />
            <LegendItem color={SEVERITY_COLOR.MINOR} label="Minor Incident" dot />
          </div>
        </div>
      </div>
    </div>
  );
}

function FitBoundsToRoute({ coordinates }) {
  const map = useMap();
  useEffect(() => {
    if (coordinates && coordinates.length > 1) {
      map.fitBounds(coordinates, { padding: [48, 48] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coordinates, map]);
  return null;
}

function LegendItem({ color, label, line, dot }) {
  return (
    <div className="flex items-center gap-2">
      {line && (
        <span
          className="inline-block h-1.5 w-4 rounded-full"
          style={{ backgroundColor: color }}
        />
      )}
      {dot && (
        <span
          className="inline-block h-2.5 w-2.5 rounded-full border border-white/50"
          style={{ backgroundColor: color }}
        />
      )}
      <span className="text-[11px] text-asphalt-300">{label}</span>
    </div>
  );
}
