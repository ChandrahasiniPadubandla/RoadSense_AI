import React, { useEffect, useState, useMemo, useRef } from 'react';
import L from 'leaflet';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Marker,
  Polyline,
  Popup,
  Tooltip,
  ZoomControl,
  useMap,
} from 'react-leaflet';
import {
  getTrafficLayer,
  getAccidentLayer,
  getHotspotsLayer,
  geocodeSearch,
  getDrivingRoute,
  reverseGeocode,
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

const HYDERABAD_CENTER = [17.43, 78.43];

// ---------------------------------------------------------------------------
// Google-Maps-style teardrop pin, built as a Leaflet divIcon (no external
// image assets, so it always renders regardless of icon-path issues).
// ---------------------------------------------------------------------------
function createPinIcon(color, label) {
  return L.divIcon({
    className: 'rs-pin-icon',
    html: `
      <div style="position:relative;width:30px;height:40px;filter:drop-shadow(0 2px 3px rgba(0,0,0,0.35));">
        <svg width="30" height="40" viewBox="0 0 30 40" xmlns="http://www.w3.org/2000/svg">
          <path d="M15 0C6.716 0 0 6.716 0 15c0 10.5 15 25 15 25s15-14.5 15-25C30 6.716 23.284 0 15 0z" fill="${color}"/>
          <circle cx="15" cy="15" r="6.5" fill="#ffffff"/>
        </svg>
        ${
          label
            ? `<div style="position:absolute;top:4px;left:0;width:30px;text-align:center;font-size:11px;font-weight:800;color:${color};line-height:1;">${label}</div>`
            : ''
        }
      </div>
    `,
    iconSize: [30, 40],
    iconAnchor: [15, 40],
    popupAnchor: [0, -36],
  });
}
const START_PIN = createPinIcon('#1E8E3E', 'A'); // Google Maps green
const END_PIN = createPinIcon('#EA4335', 'B'); // Google Maps red
const SEARCH_PIN = createPinIcon('#4285F4', ''); // Google Maps blue

// Turn-by-turn maneuver -> simple directional glyph (kept dependency-free;
// swap for an icon set later if desired).
function stepGlyph(step) {
  const type = step.maneuver_type;
  const mod = step.maneuver_modifier || '';
  if (type === 'depart') return '📍';
  if (type === 'arrive') return '🏁';
  if (type === 'roundabout' || type === 'rotary' || type === 'roundabout turn') return '🔄';
  if (mod.includes('sharp left')) return '↖';
  if (mod.includes('sharp right')) return '↗';
  if (mod.includes('left')) return '↰';
  if (mod.includes('right')) return '↱';
  if (mod === 'uturn') return '↩';
  return '↑';
}

export default function LiveMap() {
  const [trafficLayer, setTrafficLayer] = useState({ features: [] });
  const [accidentLayer, setAccidentLayer] = useState({ features: [] });
  const [hotspotsLayer, setHotspotsLayer] = useState({ features: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Layer visibility (moved into a floating "Layers" control, Google-Maps-style)
  const [layersOpen, setLayersOpen] = useState(false);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showAccidents, setShowAccidents] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [legendOpen, setLegendOpen] = useState(false);

  // ---------------------------------------------------------------------
  // Search / Directions - live OSM Nominatim geocoding + live OSRM routing
  // + live ML predictions for the resolved start/end pair. Nothing here is
  // mocked or a straight line - every value comes from a real API call.
  //
  // NOTE for future live-API swap: every network call in this component
  // goes through geocodeSearch() / getDrivingRoute() / reverseGeocode() in
  // api_services.js. To switch to Google Maps Places/Directions later,
  // change only the internals of those three functions (and their backend
  // counterparts) - this component's UI and state logic doesn't need to
  // change, since it only relies on the {latitude, longitude, display_name}
  // / {coordinates, distance_km, duration_minutes, steps} shape.
  // ---------------------------------------------------------------------
  const [directionsMode, setDirectionsMode] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [searchPoint, setSearchPoint] = useState(null); // { lat, lng, label }

  const [startQuery, setStartQuery] = useState('');
  const [endQuery, setEndQuery] = useState('');
  const [startPoint, setStartPoint] = useState(null); // { lat, lng, label }
  const [endPoint, setEndPoint] = useState(null);
  const [startSuggestions, setStartSuggestions] = useState([]);
  const [endSuggestions, setEndSuggestions] = useState([]);
  const [activeField, setActiveField] = useState(null); // 'search' | 'start' | 'end' | null

  const [routeGeometry, setRouteGeometry] = useState(null); // [[lat,lng], ...]
  const [routeInfo, setRouteInfo] = useState(null); // { distance_km, duration_minutes, is_real_route, steps }
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState('');
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [flyTarget, setFlyTarget] = useState(null); // [lat,lng] - pan map here once

  const [routeTraffic, setRouteTraffic] = useState(null);
  const [routeAccidentRisk, setRouteAccidentRisk] = useState(null);
  const [predictionsLoading, setPredictionsLoading] = useState(false);

  const [userLocation, setUserLocation] = useState(null); // { lat, lng }
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState('');

  const searchDebounce = useRef(null);
  const startDebounce = useRef(null);
  const endDebounce = useRef(null);

  // Live type-ahead search against OpenStreetMap Nominatim (debounced to
  // respect Nominatim's usage policy and avoid hammering the API on every
  // keystroke).
  useEffect(() => {
    clearTimeout(searchDebounce.current);
    if (!searchQuery || searchPoint?.label === searchQuery) {
      setSearchSuggestions([]);
      return;
    }
    searchDebounce.current = setTimeout(async () => {
      setSearchSuggestions(await geocodeSearch(searchQuery));
    }, 400);
    return () => clearTimeout(searchDebounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  useEffect(() => {
    clearTimeout(startDebounce.current);
    if (!startQuery || startPoint?.label === startQuery) {
      setStartSuggestions([]);
      return;
    }
    startDebounce.current = setTimeout(async () => {
      setStartSuggestions(await geocodeSearch(startQuery));
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
      setEndSuggestions(await geocodeSearch(endQuery));
    }, 400);
    return () => clearTimeout(endDebounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endQuery]);

  function selectSuggestion(field, suggestion) {
    const point = { lat: suggestion.latitude, lng: suggestion.longitude, label: suggestion.display_name };
    if (field === 'search') {
      setSearchPoint(point);
      setSearchQuery(suggestion.display_name);
      setSearchSuggestions([]);
      setFlyTarget([point.lat, point.lng]);
    } else if (field === 'start') {
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

  function openDirections(prefillStart) {
    setDirectionsMode(true);
    setSearchQuery('');
    setSearchPoint(null);
    setSearchSuggestions([]);
    if (prefillStart) {
      setStartPoint(prefillStart);
      setStartQuery(prefillStart.label);
    }
  }

  function swapStartEnd() {
    const s = startPoint;
    const sq = startQuery;
    setStartPoint(endPoint);
    setStartQuery(endQuery);
    setEndPoint(s);
    setEndQuery(sq);
  }

  function locateMe(useAsStart) {
    if (!navigator.geolocation) {
      setLocateError('Your browser does not support geolocation.');
      return;
    }
    setLocating(true);
    setLocateError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLocation({ lat, lng });
        setFlyTarget([lat, lng]);

        let label = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        try {
          const place = await reverseGeocode(lat, lng);
          if (place?.display_name) label = place.display_name;
        } catch {
          /* keep the coordinate fallback label */
        }

        if (useAsStart) {
          setDirectionsMode(true);
          setStartPoint({ lat, lng, label });
          setStartQuery(label);
        }
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        setLocateError(err.code === 1 ? 'Location permission denied.' : 'Could not get your location.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
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
    setStepsExpanded(true);

    try {
      // Live OSRM routing - real street-level geometry + turn-by-turn steps.
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
    // same start/end pair. Best-effort: if the model can't resolve the
    // locations to a known road, we just omit that card.
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
    setDirectionsMode(false);
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
    return HYDERABAD_CENTER;
  }, [trafficLayer]);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center rounded-lg border border-slate-200 dark:border-asphalt-700 bg-white dark:bg-asphalt-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-signal-blue border-t-transparent"></div>
          <p className="text-sm font-medium text-slate-600 dark:text-asphalt-300">
            Loading live map layers from backend APIs...
          </p>
        </div>
      </div>
    );
  }

  const roadCount = trafficLayer?.features?.length || 0;
  const accidentCount = accidentLayer?.features?.length || 0;
  const hotspotCount = hotspotsLayer?.features?.length || 0;
  const anyDataMissing =
    roadCount === 0 || accidentCount === 0 || hotspotCount === 0 || (accidentCount > 0 && filteredAccidents.length === 0);

  const panelInputClass =
    'w-full rounded-md border-0 bg-transparent px-1 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-asphalt-100 dark:placeholder:text-asphalt-500';

  return (
    // Full-bleed map, Google-Maps-style: the map fills the available space
    // and everything else (search, directions, layers, legend, zoom, locate)
    // floats on top of it as overlay controls.
    <div className="relative h-[calc(100vh-7.5rem)] overflow-hidden rounded-lg border border-slate-200 dark:border-asphalt-700">
      <MapContainer center={mapCenter} zoom={12} zoomControl={false} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ZoomControl position="bottomright" />
        {flyTarget && <FlyToPoint coordinate={flyTarget} />}

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
                      <p className="text-asphalt-600">{p.road_type} - Speed Limit: {p.speed_limit} km/h</p>
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
                      <p><strong>Casualties:</strong> {p.fatalities || 0} fatal - {p.injuries || 0} injured</p>
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

        {/* Route: real OSRM route geometry + Google-style A/B pins */}
        {routeGeometry && routeGeometry.length > 1 && (
          <>
            <Polyline
              positions={routeGeometry}
              pathOptions={{ color: '#4285F4', weight: 6, opacity: 0.95, lineCap: 'round', lineJoin: 'round' }}
            />
            <FitBoundsToRoute coordinates={routeGeometry} />
          </>
        )}
        {startPoint && (
          <Marker position={[startPoint.lat, startPoint.lng]} icon={START_PIN}>
            <Popup>Start: {startPoint.label}</Popup>
          </Marker>
        )}
        {endPoint && (
          <Marker position={[endPoint.lat, endPoint.lng]} icon={END_PIN}>
            <Popup>Destination: {endPoint.label}</Popup>
          </Marker>
        )}
        {searchPoint && !directionsMode && (
          <Marker position={[searchPoint.lat, searchPoint.lng]} icon={SEARCH_PIN}>
            <Popup>
              <div className="text-xs text-asphalt-900">
                <p className="mb-1 font-semibold">{searchPoint.label}</p>
                <button
                  onClick={() => openDirections()}
                  className="rounded bg-signal-blue px-2 py-1 text-[11px] font-medium text-white"
                >
                  Directions from here
                </button>
              </div>
            </Popup>
          </Marker>
        )}

        {/* "My location" - Google-Maps-style blue dot with halo */}
        {userLocation && (
          <>
            <CircleMarker
              center={[userLocation.lat, userLocation.lng]}
              radius={14}
              pathOptions={{ color: 'transparent', fillColor: '#4285F4', fillOpacity: 0.18, weight: 0 }}
            />
            <CircleMarker
              center={[userLocation.lat, userLocation.lng]}
              radius={7}
              pathOptions={{ color: '#ffffff', fillColor: '#4285F4', fillOpacity: 1, weight: 3 }}
            >
              <Tooltip>You are here</Tooltip>
            </CircleMarker>
          </>
        )}
      </MapContainer>

      {/* ------------------------------------------------------------- */}
      {/* Floating Search / Directions panel - top-left, Google-Maps-style */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute left-3 top-3 z-[1000] w-[min(92vw,380px)]">
        <div className="max-h-[85vh] overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
          {!directionsMode ? (
            // ---- Single search box mode ------------------------------
            <div className="p-2">
              <div className="relative flex items-center gap-2 rounded-lg border border-slate-200 px-3 dark:border-asphalt-700">
                <span className="text-slate-400 dark:text-asphalt-500">🔍</span>
                <input
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSearchPoint(null);
                  }}
                  onFocus={() => setActiveField('search')}
                  placeholder="Search RoadSense Maps"
                  className={panelInputClass}
                />
                {searchQuery && (
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setSearchPoint(null);
                      setSearchSuggestions([]);
                    }}
                    className="text-slate-400 hover:text-slate-700 dark:text-asphalt-500 dark:hover:text-asphalt-200"
                  >
                    ✕
                  </button>
                )}
              </div>

              {activeField === 'search' && searchSuggestions.length > 0 && (
                <ul className="mt-1 max-h-56 overflow-y-auto rounded-md border border-slate-200 dark:border-asphalt-700">
                  {searchSuggestions.map((s, i) => (
                    <li
                      key={i}
                      onMouseDown={() => selectSuggestion('search', s)}
                      className="cursor-pointer px-3 py-2 text-xs text-slate-700 hover:bg-slate-100 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
                    >
                      {s.display_name}
                    </li>
                  ))}
                </ul>
              )}

              <button
                onClick={() => openDirections()}
                className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-signal-blue transition-colors hover:bg-signal-blue/10"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-signal-blue/15">↗</span>
                Directions
              </button>

              <button
                onClick={() => locateMe(false)}
                disabled={locating}
                className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 disabled:opacity-50 dark:text-asphalt-300 dark:hover:bg-asphalt-800"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 dark:bg-asphalt-800">◉</span>
                {locating ? 'Finding you...' : 'Show my location'}
              </button>
              {locateError && <p className="px-3 pb-1 text-xs text-signal-red">{locateError}</p>}
            </div>
          ) : (
            // ---- Directions mode (A -> B), Google-Maps-style -----------
            <div className="p-2">
              <div className="flex items-center gap-2 px-1 pb-1">
                <button
                  onClick={handleClearRoute}
                  className="flex h-7 w-7 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 dark:text-asphalt-400 dark:hover:bg-asphalt-800"
                  aria-label="Close directions"
                >
                  ←
                </button>
                <p className="text-sm font-semibold text-slate-900 dark:text-asphalt-100">Directions</p>
              </div>

              <div className="flex gap-2">
                {/* A/B connector rail */}
                <div className="flex flex-col items-center pt-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#1E8E3E]" />
                  <span className="my-1 h-8 w-px border-l border-dotted border-slate-300 dark:border-asphalt-600" />
                  <span className="h-2.5 w-2.5 rounded-sm bg-[#EA4335]" />
                </div>

                <div className="flex-1 space-y-1.5">
                  <div className="relative rounded-lg border border-slate-200 px-3 dark:border-asphalt-700">
                    <input
                      value={startQuery}
                      onChange={(e) => {
                        setStartQuery(e.target.value);
                        setStartPoint(null);
                      }}
                      onFocus={() => setActiveField('start')}
                      placeholder="Choose starting point"
                      className={panelInputClass}
                    />
                    {activeField === 'start' && startSuggestions.length > 0 && (
                      <ul className="absolute left-0 right-0 top-full z-[1100] mt-1 max-h-56 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-xl dark:border-asphalt-700 dark:bg-asphalt-900">
                        {startSuggestions.map((s, i) => (
                          <li
                            key={i}
                            onMouseDown={() => selectSuggestion('start', s)}
                            className="cursor-pointer px-3 py-2 text-xs text-slate-700 hover:bg-slate-100 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
                          >
                            {s.display_name}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="relative rounded-lg border border-slate-200 px-3 dark:border-asphalt-700">
                    <input
                      value={endQuery}
                      onChange={(e) => {
                        setEndQuery(e.target.value);
                        setEndPoint(null);
                      }}
                      onFocus={() => setActiveField('end')}
                      placeholder="Choose destination"
                      className={panelInputClass}
                    />
                    {activeField === 'end' && endSuggestions.length > 0 && (
                      <ul className="absolute left-0 right-0 top-full z-[1100] mt-1 max-h-56 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-xl dark:border-asphalt-700 dark:bg-asphalt-900">
                        {endSuggestions.map((s, i) => (
                          <li
                            key={i}
                            onMouseDown={() => selectSuggestion('end', s)}
                            className="cursor-pointer px-3 py-2 text-xs text-slate-700 hover:bg-slate-100 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
                          >
                            {s.display_name}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                <button
                  onClick={swapStartEnd}
                  title="Swap start and destination"
                  className="flex h-8 w-8 shrink-0 items-center justify-center self-center rounded-full text-slate-500 hover:bg-slate-100 dark:text-asphalt-400 dark:hover:bg-asphalt-800"
                >
                  ⇅
                </button>
              </div>

              <div className="flex items-center justify-between px-1 pt-1.5">
                <button
                  onClick={() => locateMe(true)}
                  disabled={locating}
                  className="text-xs font-medium text-signal-blue hover:underline disabled:opacity-50"
                >
                  {locating ? 'Finding you...' : 'Use my current location'}
                </button>
                <button
                  onClick={handleFindRoute}
                  disabled={routeLoading || !startPoint || !endPoint}
                  className="rounded-md bg-signal-blue px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {routeLoading ? 'Routing...' : 'Get Directions'}
                </button>
              </div>

              {(routeError || locateError) && (
                <p className="mt-1 px-1 text-xs text-signal-red">{routeError || locateError}</p>
              )}

              {routeInfo && (
                <div className="mt-2 border-t border-slate-200 pt-2 dark:border-asphalt-800">
                  <div className="flex flex-wrap items-center gap-2 px-1 text-xs">
                    <span className="text-lg font-bold text-slate-900 dark:text-asphalt-100">
                      {routeInfo.duration_minutes} min
                    </span>
                    <span className="text-slate-500 dark:text-asphalt-400">({routeInfo.distance_km} km)</span>
                    <span
                      className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        routeInfo.is_real_route
                          ? 'bg-signal-blue/10 text-signal-blue'
                          : 'bg-signal-amber/10 text-signal-amber'
                      }`}
                    >
                      {routeInfo.is_real_route ? 'Live route via OSRM' : 'Approximate route'}
                    </span>
                  </div>

                  <div className="mt-1.5 flex flex-wrap gap-1.5 px-1">
                    {predictionsLoading && (
                      <span className="text-[11px] text-slate-400 dark:text-asphalt-500">
                        Running live traffic/accident-risk models...
                      </span>
                    )}
                    {routeTraffic && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-signal-amber/40 bg-signal-amber/10 px-2 py-0.5 text-[11px] font-medium text-signal-amber">
                        Congestion: {routeTraffic.congestion_level}
                      </span>
                    )}
                    {routeAccidentRisk && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-signal-red/40 bg-signal-red/10 px-2 py-0.5 text-[11px] font-medium text-signal-red">
                        Accident risk: {routeAccidentRisk.risk_level}
                        {routeAccidentRisk.risk_percentage != null
                          ? ` (${Number(routeAccidentRisk.risk_percentage).toFixed(0)}%)`
                          : ''}
                      </span>
                    )}
                  </div>

                  {routeInfo.steps?.length > 0 && (
                    <div className="mt-2">
                      <button
                        onClick={() => setStepsExpanded((v) => !v)}
                        className="flex w-full items-center justify-between px-1 py-1 text-xs font-semibold text-slate-700 dark:text-asphalt-200"
                      >
                        <span>Turn-by-turn directions ({routeInfo.steps.length})</span>
                        <span>{stepsExpanded ? '▲' : '▼'}</span>
                      </button>
                      {stepsExpanded && (
                        <ol className="max-h-64 space-y-0.5 overflow-y-auto">
                          {routeInfo.steps.map((step, i) => (
                            <li key={i}>
                              <button
                                onClick={() => step.coordinates && setFlyTarget(step.coordinates)}
                                className="flex w-full items-start gap-2 rounded-md px-1.5 py-1.5 text-left text-xs hover:bg-slate-100 dark:hover:bg-asphalt-800"
                              >
                                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] dark:bg-asphalt-800">
                                  {stepGlyph(step)}
                                </span>
                                <span className="flex-1 text-slate-700 dark:text-asphalt-200">
                                  {step.instruction}
                                  {step.distance_meters > 0 && (
                                    <span className="ml-1 text-slate-400 dark:text-asphalt-500">
                                      {' '}-{' '}
                                      {step.distance_meters >= 1000
                                        ? `${(step.distance_meters / 1000).toFixed(1)} km`
                                        : `${Math.round(step.distance_meters)} m`}
                                    </span>
                                  )}
                                </span>
                              </button>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Floating "Layers" control - bottom-left, Google-Maps-style      */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute bottom-3 left-3 z-[1000]">
        {layersOpen && (
          <div className="mb-2 w-64 rounded-xl border border-slate-200 bg-white p-3 text-xs shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
            <p className="mb-2 font-semibold text-slate-900 dark:text-asphalt-100">Map layers</p>

            <label className="mb-1.5 flex items-center justify-between gap-2 rounded-md px-1 py-1 hover:bg-slate-50 dark:hover:bg-asphalt-800">
              <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200">
                <span className="h-2 w-2 rounded-full bg-signal-blue" /> Traffic roads ({roadCount})
              </span>
              <input type="checkbox" checked={showTraffic} onChange={() => setShowTraffic((v) => !v)} />
            </label>
            <label className="mb-1.5 flex items-center justify-between gap-2 rounded-md px-1 py-1 hover:bg-slate-50 dark:hover:bg-asphalt-800">
              <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200">
                <span className="h-2 w-2 rounded-full bg-signal-red" /> Accident markers ({accidentCount})
              </span>
              <input type="checkbox" checked={showAccidents} onChange={() => setShowAccidents((v) => !v)} />
            </label>
            <label className="mb-2 flex items-center justify-between gap-2 rounded-md px-1 py-1 hover:bg-slate-50 dark:hover:bg-asphalt-800">
              <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200">
                <span className="h-2 w-2 rounded-full bg-signal-amber" /> Accident hotspots ({hotspotCount})
              </span>
              <input type="checkbox" checked={showHotspots} onChange={() => setShowHotspots((v) => !v)} />
            </label>

            <div className="mb-2 flex items-center gap-1.5 border-t border-slate-200 pt-2 dark:border-asphalt-800">
              <span className="text-slate-500 dark:text-asphalt-400">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="flex-1 rounded border border-slate-200 bg-slate-50 px-1.5 py-1 text-slate-800 outline-none focus:border-signal-blue dark:border-asphalt-700 dark:bg-asphalt-800 dark:text-asphalt-200"
              >
                <option value="ALL">All severities</option>
                <option value="SEVERE_FATAL">Severe & fatal only</option>
                <option value="MODERATE_MINOR">Moderate & minor</option>
              </select>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 pt-2 dark:border-asphalt-800">
              <span className="text-slate-400 dark:text-asphalt-500">
                {lastUpdated ? `Synced ${lastUpdated}` : 'Not yet synced'}
              </span>
              <button
                onClick={loadMapData}
                className="rounded bg-slate-100 px-2 py-1 font-medium text-slate-700 hover:bg-slate-200 dark:bg-asphalt-800 dark:text-asphalt-200 dark:hover:bg-asphalt-700"
              >
                Refresh
              </button>
            </div>

            {anyDataMissing && (
              <div className="mt-2 space-y-1 border-t border-slate-200 pt-2 dark:border-asphalt-800">
                {roadCount === 0 && <p className="text-slate-500 dark:text-asphalt-400">No traffic segments available.</p>}
                {accidentCount === 0 && <p className="text-slate-500 dark:text-asphalt-400">No accidents recorded.</p>}
                {hotspotCount === 0 && showHotspots && (
                  <p className="text-slate-500 dark:text-asphalt-400">No hotspots registered yet.</p>
                )}
                {accidentCount > 0 && filteredAccidents.length === 0 && (
                  <p className="text-signal-amber">No accidents match this severity filter.</p>
                )}
              </div>
            )}
          </div>
        )}
        <button
          onClick={() => setLayersOpen((v) => !v)}
          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-xl transition-colors hover:bg-slate-50 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
        >
          🗂 Layers
        </button>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Floating "Locate me" control - sits just above the zoom control */}
      {/* ------------------------------------------------------------- */}
      <button
        onClick={() => locateMe(false)}
        disabled={locating}
        title="Show my location"
        className="absolute bottom-[7.5rem] right-3 z-[1000] flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-base text-signal-blue shadow-xl transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-asphalt-700 dark:bg-asphalt-900 dark:hover:bg-asphalt-800"
      >
        {locating ? '…' : '◉'}
      </button>

      {/* ------------------------------------------------------------- */}
      {/* Floating Legend - top-right, collapsible                       */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute right-3 top-3 z-[1000] w-56 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
        <button
          onClick={() => setLegendOpen((v) => !v)}
          className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold text-slate-900 dark:text-asphalt-100"
        >
          <span>Live Map Legend</span>
          <span>{legendOpen ? '▲' : '▼'}</span>
        </button>
        {legendOpen && (
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-slate-200 p-3 text-xs dark:border-asphalt-800">
            <LegendItem color={CONGESTION_COLOR.LOW} label="Low Traffic (<40%)" line />
            <LegendItem color={CONGESTION_COLOR.MEDIUM} label="Medium Traffic" line />
            <LegendItem color={CONGESTION_COLOR.HIGH} label="High Congestion" line />
            <LegendItem color={CONGESTION_COLOR.SEVERE} label="Severe (>85%)" line />
            <LegendItem color={SEVERITY_COLOR.FATAL} label="Fatal Accident" dot />
            <LegendItem color={SEVERITY_COLOR.SEVERE} label="Severe Accident" dot />
            <LegendItem color={SEVERITY_COLOR.MODERATE} label="Moderate Incident" dot />
            <LegendItem color={SEVERITY_COLOR.MINOR} label="Minor Incident" dot />
          </div>
        )}
      </div>
    </div>
  );
}

function FitBoundsToRoute({ coordinates }) {
  const map = useMap();
  useEffect(() => {
    if (coordinates && coordinates.length > 1) {
      map.fitBounds(coordinates, { padding: [220, 48] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coordinates, map]);
  return null;
}

function FlyToPoint({ coordinate }) {
  const map = useMap();
  useEffect(() => {
    if (coordinate) {
      map.flyTo(coordinate, Math.max(map.getZoom(), 14), { duration: 0.75 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coordinate, map]);
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
      <span className="text-[11px] text-slate-600 dark:text-asphalt-300">{label}</span>
    </div>
  );
}
