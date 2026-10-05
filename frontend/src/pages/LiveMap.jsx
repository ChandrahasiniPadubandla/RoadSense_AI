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
  getAnomaliesLayer,
  geocodeSearch,
  getDrivingRoute,
  reverseGeocode,
  predictRouteTraffic,
  predictRouteAccident,
} from '../api_services';
import VoiceAssistant from '../components/VoiceAssistant';

// Background traffic-road layer colors (unchanged 4-tier scale, used for the
// city-wide road overlay you toggle in "Layers").
const CONGESTION_COLOR = {
  LOW: '#10B981',
  MEDIUM: '#F59E0B',
  HIGH: '#F97316',
  SEVERE: '#EF4444',
  UNKNOWN: '#9CA3AF',
};

// Route-specific colors: Google-Maps-style traffic palette — green for clear/low,
// yellow/amber for medium/moderate, red for high, crimson for severe.
const ROUTE_CONGESTION_COLOR = {
  LOW: '#10B981',
  MEDIUM: '#F59E0B',
  HIGH: '#EF4444',
  SEVERE: '#991B1B',
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

function formatClockTime(date) {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) return '';
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
}

// ---------------------------------------------------------------------------
// Distance helper (module scope so both navigation tracking AND the
// route-congestion / route-hotspot matching below can use it).
// ---------------------------------------------------------------------------
function haversineMeters(lat1, lng1, lat2, lng2) {
  const R = 6371000;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Finds the CLOSEST traffic-layer road vertex to a point — no distance
// cutoff, so every point along a route always gets some congestion color,
// the same way Google Maps colors a whole route rather than leaving gaps.
// `closeThresholdMeters` just marks whether the match is close enough to
// trust strongly (used to tag the tooltip as an estimate vs. a real reading).
function nearestCongestionMatch(lat, lng, trafficFeatures, closeThresholdMeters = 300) {
  let best = null;
  let bestDist = Infinity;
  for (const f of trafficFeatures) {
    const coords = f.geometry?.coordinates;
    if (!coords) continue;
    for (const [rlng, rlat] of coords) {
      const d = haversineMeters(lat, lng, rlat, rlng);
      if (d < bestDist) {
        bestDist = d;
        best = f.properties;
      }
    }
  }
  if (!best) return null;
  return { ...best, _distanceMeters: bestDist, _isEstimate: bestDist > closeThresholdMeters };
}

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

function getCategoryBadge(category) {
  if (category === 'corridor') {
    return { icon: '🛣️', badge: 'Monitored Corridor', color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' };
  }
  if (category === 'transit') {
    return { icon: '🚌', badge: 'Bus Station / Transit', color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20' };
  }
  if (category === 'poi') {
    return { icon: '🏛️', badge: 'Landmark', color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' };
  }
  return { icon: '📍', badge: 'Location', color: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20' };
}

export default function LiveMap() {
  const [trafficLayer, setTrafficLayer] = useState({ features: [] });
  const [accidentLayer, setAccidentLayer] = useState({ features: [] });
  const [hotspotsLayer, setHotspotsLayer] = useState({ features: [] });
  const [anomalyLayer, setAnomalyLayer] = useState({ features: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Route layer visibility - controls overlays along the selected direction
  const [layersOpen, setLayersOpen] = useState(false);
  const [showRouteTraffic, setShowRouteTraffic] = useState(true);
  const [showRouteHotspots, setShowRouteHotspots] = useState(true);
  const [showRouteAccidents, setShowRouteAccidents] = useState(true);
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
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [routeError, setRouteError] = useState('');
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [flyTarget, setFlyTarget] = useState(null); // [lat,lng] - pan map here once

  const [routeTraffic, setRouteTraffic] = useState(null);
  const [routeAccidentRisk, setRouteAccidentRisk] = useState(null);
  const [predictionsLoading, setPredictionsLoading] = useState(false);

  // ---------------------------------------------------------------------
  // Prediction / Departure Time Controls (Active & Present by Default)
  // ---------------------------------------------------------------------
  const [departureOption, setDepartureOption] = useState('30m'); // 'now' | '15m' | '30m' (default) | '1h' | 'peak_evening' | 'peak_morning' | 'custom'
  const [customTime, setCustomTime] = useState(''); // "HH:MM"

  // Resolves the effective target Date object based on chosen option
  const resolvedTargetDate = useMemo(() => {
    const d = new Date();
    if (departureOption === 'now') {
      return d;
    }
    if (departureOption === '15m') {
      return new Date(d.getTime() + 15 * 60 * 1000);
    }
    if (departureOption === '30m') {
      return new Date(d.getTime() + 30 * 60 * 1000);
    }
    if (departureOption === '1h') {
      return new Date(d.getTime() + 60 * 60 * 1000);
    }
    if (departureOption === 'peak_evening') {
      const peak = new Date(d);
      peak.setHours(18, 0, 0, 0); // 6:00 PM
      return peak;
    }
    if (departureOption === 'peak_morning') {
      const peak = new Date(d);
      peak.setHours(9, 0, 0, 0); // 9:00 AM
      return peak;
    }
    if (departureOption === 'custom' && customTime) {
      const [hh, mm] = customTime.split(':').map(Number);
      if (!isNaN(hh) && !isNaN(mm)) {
        const custom = new Date(d);
        custom.setHours(hh, mm, 0, 0);
        return custom;
      }
    }
    return new Date(d.getTime() + 30 * 60 * 1000);
  }, [departureOption, customTime]);

  // Estimated arrival time calculated from target time + route duration
  const estimatedArrivalTime = useMemo(() => {
    if (!resolvedTargetDate || !routeInfo?.duration_minutes) return null;
    return new Date(resolvedTargetDate.getTime() + routeInfo.duration_minutes * 60 * 1000);
  }, [resolvedTargetDate, routeInfo?.duration_minutes]);

  // Builds the prediction request payload for a specific target date
  function buildPredictionPayload(targetDate, sp = startPoint, ep = endPoint) {
    if (!sp || !ep) return null;
    const pad = (n) => String(n).padStart(2, '0');
    const yyyy = targetDate.getFullYear();
    const MM = pad(targetDate.getMonth() + 1);
    const dd = pad(targetDate.getDate());
    const hh = pad(targetDate.getHours());
    const mm = pad(targetDate.getMinutes());
    const ss = pad(targetDate.getSeconds());
    const localIso = `${yyyy}-${MM}-${dd}T${hh}:${mm}:${ss}`;

    const diffMins = Math.max(5, Math.round((targetDate.getTime() - Date.now()) / 60000));

    return {
      start_location: sp.label,
      end_location: ep.label,
      start_latitude: sp.lat,
      start_longitude: sp.lng,
      end_latitude: ep.lat,
      end_longitude: ep.lng,
      target_time: localIso,
      target_minutes_ahead: diffMins,
    };
  }

  // Updates predictions whenever the user switches the departure/prediction time
  async function updatePredictionsForTime(targetDate) {
    if (!startPoint || !endPoint) return;
    const payload = buildPredictionPayload(targetDate);
    if (!payload) return;

    setPredictionsLoading(true);
    try {
      const [trafficResult, accidentResult] = await Promise.allSettled([
        predictRouteTraffic(payload),
        predictRouteAccident(payload),
      ]);
      if (trafficResult.status === 'fulfilled') setRouteTraffic(trafficResult.value);
      if (accidentResult.status === 'fulfilled') setRouteAccidentRisk(accidentResult.value);
    } catch (err) {
      console.error('Failed to update route predictions for time:', err);
    } finally {
      setPredictionsLoading(false);
    }
  }

  function handleDepartureOptionSelect(opt) {
    setDepartureOption(opt);
    if (routeGeometry && startPoint && endPoint) {
      const d = new Date();
      let target;
      if (opt === 'now') target = d;
      else if (opt === '15m') target = new Date(d.getTime() + 15 * 60 * 1000);
      else if (opt === '30m') target = new Date(d.getTime() + 30 * 60 * 1000);
      else if (opt === '1h') target = new Date(d.getTime() + 60 * 60 * 1000);
      else if (opt === 'peak_evening') {
        target = new Date(d);
        target.setHours(18, 0, 0, 0);
      } else if (opt === 'peak_morning') {
        target = new Date(d);
        target.setHours(9, 0, 0, 0);
      } else if (opt === 'custom' && customTime) {
        const [hh, mm] = customTime.split(':').map(Number);
        if (!isNaN(hh) && !isNaN(mm)) {
          target = new Date(d);
          target.setHours(hh, mm, 0, 0);
        } else {
          target = new Date(d.getTime() + 30 * 60 * 1000);
        }
      } else {
        target = new Date(d.getTime() + 30 * 60 * 1000);
      }
      updatePredictionsForTime(target);
    }
  }

  function handleCustomTimeChange(val) {
    setCustomTime(val);
    setDepartureOption('custom');
    if (routeGeometry && startPoint && endPoint && val) {
      const [hh, mm] = val.split(':').map(Number);
      if (!isNaN(hh) && !isNaN(mm)) {
        const d = new Date();
        d.setHours(hh, mm, 0, 0);
        updatePredictionsForTime(d);
      }
    }
  }

  // ---------------------------------------------------------------------
  // "Start" live navigation — Google-Maps-style turn-by-turn tracking using
  // the browser's real GPS (navigator.geolocation.watchPosition). Follows
  // the user's live position, advances to the nearest upcoming step
  // automatically, and shows a bottom navigation banner.
  // ---------------------------------------------------------------------
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [navError, setNavError] = useState('');
  const watchIdRef = useRef(null);

  function startNavigation() {
    if (!navigator.geolocation) {
      setNavError('Your browser does not support live GPS tracking.');
      return;
    }
    if (!routeInfo?.steps?.length) {
      setNavError('No turn-by-turn steps available for this route.');
      return;
    }
    setNavError('');
    setCurrentStepIndex(0);
    setIsNavigating(true);

    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLocation({ lat, lng });
        setFlyTarget([lat, lng]);

        // Advance to whichever upcoming step's maneuver point is now
        // closest — a simple but effective way to track progress without
        // needing full route map-matching.
        setCurrentStepIndex((prevIndex) => {
          const steps = routeInfo.steps;
          let bestIndex = prevIndex;
          let bestDist = Infinity;
          for (let i = prevIndex; i < steps.length; i++) {
            const coord = steps[i].coordinates;
            if (!coord) continue;
            const d = haversineMeters(lat, lng, coord[0], coord[1]);
            if (d < bestDist) {
              bestDist = d;
              bestIndex = i;
            }
            // Once we're clearly closer to a later step than the current
            // one, and within arrival range of it, advance to it.
            if (i > prevIndex && d < 40) {
              bestIndex = Math.min(i + 1, steps.length - 1);
            }
          }
          return bestIndex;
        });
      },
      (err) => {
        setNavError(err.code === 1 ? 'Location permission denied.' : 'Lost GPS signal.');
      },
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 }
    );
  }

  function stopNavigation() {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setIsNavigating(false);
    setCurrentStepIndex(0);
  }

  useEffect(() => {
    // Safety net: stop any active GPS watch if the component unmounts
    // mid-navigation (e.g. the user clicks away to another page).
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

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
    const label = suggestion.primary_name
      ? (suggestion.secondary_name ? `${suggestion.primary_name}, ${suggestion.secondary_name}` : suggestion.primary_name)
      : suggestion.display_name;
    const point = {
      lat: suggestion.latitude,
      lng: suggestion.longitude,
      label: label,
      category: suggestion.category
    };
    if (field === 'search') {
      setSearchPoint(point);
      setSearchQuery(label);
      setSearchSuggestions([]);
      setFlyTarget([point.lat, point.lng]);
    } else if (field === 'start') {
      setStartPoint(point);
      setStartQuery(label);
      setStartSuggestions([]);
    } else {
      setEndPoint(point);
      setEndQuery(label);
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

  // Fetches the live route + ML predictions for an explicit start/end pair.
  // (Voice input calls this directly because React state hasn't updated yet.)
  async function runRoute(sp, ep) {
    if (!sp || !ep) {
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
      const route = await getDrivingRoute(sp.lat, sp.lng, ep.lat, ep.lng);
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
    const payload = buildPredictionPayload(resolvedTargetDate, sp, ep) || {
      start_location: sp.label,
      end_location: ep.label,
      start_latitude: sp.lat,
      start_longitude: sp.lng,
      end_latitude: ep.lat,
      end_longitude: ep.lng,
      target_minutes_ahead: 30,
    };
    const [trafficResult, accidentResult] = await Promise.allSettled([
      predictRouteTraffic(payload),
      predictRouteAccident(payload),
    ]);
    if (trafficResult.status === 'fulfilled') setRouteTraffic(trafficResult.value);
    if (accidentResult.status === 'fulfilled') setRouteAccidentRisk(accidentResult.value);
    setPredictionsLoading(false);
  }

  function handleFindRoute() {
    return runRoute(startPoint, endPoint);
  }

  // Turns a geocoder suggestion into the { lat, lng, label } shape used above
  // (same label rules as selectSuggestion).
  function suggestionToPoint(suggestion) {
    const label = suggestion.primary_name
      ? (suggestion.secondary_name ? `${suggestion.primary_name}, ${suggestion.secondary_name}` : suggestion.primary_name)
      : suggestion.display_name;
    return {
      lat: suggestion.latitude,
      lng: suggestion.longitude,
      label,
      category: suggestion.category,
    };
  }

  // Voice assistant: "directions from Uppal to Nagole" -> geocode both places,
  // fill the A/B boxes and draw the route. Uses the best geocoder match for
  // each spoken place; the resolved names stay visible in the boxes so the
  // user can correct them if the wrong place was picked.
  async function handleVoiceRoute(voice) {
    const startText = voice.start_location;
    const endText = voice.end_location;

    setDirectionsMode(true);
    setSearchQuery('');
    setSearchPoint(null);
    setSearchSuggestions([]);
    setStartSuggestions([]);
    setEndSuggestions([]);
    setActiveField(null);
    setRouteError('');
    setVoiceBusy(true);

    try {
      const [startResults, endResults] = await Promise.all([
        startText ? geocodeSearch(startText) : Promise.resolve(null),
        endText ? geocodeSearch(endText) : Promise.resolve(null),
      ]);

      let sp = startPoint;
      let ep = endPoint;
      const notFound = [];

      if (startText) {
        const match = startResults?.[0];
        if (match) {
          sp = suggestionToPoint(match);
          setStartPoint(sp);
          setStartQuery(sp.label);
        } else {
          sp = null;
          setStartPoint(null);
          setStartQuery(startText);
          notFound.push(startText);
        }
      }

      if (endText) {
        const match = endResults?.[0];
        if (match) {
          ep = suggestionToPoint(match);
          setEndPoint(ep);
          setEndQuery(ep.label);
        } else {
          ep = null;
          setEndPoint(null);
          setEndQuery(endText);
          notFound.push(endText);
        }
      }

      if (notFound.length > 0) {
        setRouteError(
          `Couldn't find ${notFound.map((n) => `“${n}”`).join(' or ')} on the map. Try a more specific place name.`
        );
        return;
      }

      // Both places were heard and located -> go straight to the route.
      if (voice.success && sp && ep) {
        await runRoute(sp, ep);
      }
    } catch (err) {
      console.error('Voice route lookup failed:', err);
      setRouteError('Could not look up those places. Please try again.');
    } finally {
      setVoiceBusy(false);
    }
  }

  function handleClearRoute() {
    stopNavigation();
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
      const [trafficRes, accidentRes, hotspotsRes, anomalyRes] = await Promise.all([
        getTrafficLayer(),
        getAccidentLayer(),
        getHotspotsLayer(),
        getAnomaliesLayer(),
      ]);
      setTrafficLayer(trafficRes || { features: [] });
      setAccidentLayer(accidentRes || { features: [] });
      setHotspotsLayer(hotspotsRes || { features: [] });
      setAnomalyLayer(anomalyRes || { features: [] });
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

  // Route overlays and ML predictions are scoped specifically to the active selected route

  // ---------------------------------------------------------------------
  // Route-aware overlays: once a route exists, color each stretch of it by
  // the congestion of the nearest real traffic segment, and flag any
  // accident hotspot that lies close to the path.
  // ---------------------------------------------------------------------

  // Route colored by the ML model's traffic prediction for the chosen time.
  // Direct route coloring from routeTraffic prediction so changes in target time
  // immediately update the route's traffic color (Green, Yellow, Red, Crimson)
  // without displaying background database road data.
  const routeCongestionSegments = useMemo(() => {
    if (!routeGeometry || routeGeometry.length < 2) {
      return null;
    }
    const defaultLevel = routeTraffic?.congestion_level || 'LOW';
    const defaultColor = ROUTE_CONGESTION_COLOR[defaultLevel] || '#10B981';

    return [
      {
        positions: routeGeometry,
        color: defaultColor,
        congestion: defaultLevel,
        roadName: routeTraffic?.road_name,
        isEstimate: false,
      }
    ];
  }, [routeGeometry, routeTraffic]);

  // ---------------------------------------------------------------------
  // Hotspots that lie along the current selected route/direction
  // (Visible ONLY when a direction/route is selected)
  // ---------------------------------------------------------------------
  const routeHotspots = useMemo(() => {
    if (!routeGeometry || routeGeometry.length < 2 || !hotspotsLayer?.features?.length) {
      return [];
    }
    const THRESHOLD_M = 300;
    return hotspotsLayer.features.filter((f) => {
      const coords = f.geometry?.coordinates;
      if (!coords) return false;
      const [lng, lat] = coords;
      return routeGeometry.some(([rlat, rlng]) => haversineMeters(lat, lng, rlat, rlng) < THRESHOLD_M);
    });
  }, [routeGeometry, hotspotsLayer]);

  // ---------------------------------------------------------------------
  // Accident Predictions & Incident Points along the current selected route/direction
  // (Visible ONLY when a direction/route is selected)
  // ---------------------------------------------------------------------
  const routeAccidents = useMemo(() => {
    if (!routeGeometry || routeGeometry.length < 2) {
      return [];
    }
    const points = [];
    const seen = new Set();

    // 1. From ML accident/traffic model responses for this specific route
    const mlPoints = routeAccidentRisk?.accident_points || routeTraffic?.accident_points || [];
    for (const pt of mlPoints) {
      const lat = pt.latitude || pt.lat;
      const lng = pt.longitude || pt.lng;
      if (lat && lng) {
        const key = `${Number(lat).toFixed(4)},${Number(lng).toFixed(4)}`;
        if (!seen.has(key)) {
          seen.add(key);
          points.push({
            id: pt.id || key,
            lat: Number(lat),
            lng: Number(lng),
            type: pt.type || 'predicted_risk_zone',
            severity: pt.severity || routeAccidentRisk?.risk_level || 'HIGH',
            risk_percentage: pt.risk_percentage ?? routeAccidentRisk?.risk_percentage,
            title: pt.title || `Predicted Accident Risk: ${pt.severity || 'HIGH'}`,
            description: pt.description || 'AI model identified this sector as an accident hazard on your route.',
            road_name: routeAccidentRisk?.road_name || routeTraffic?.road_name || 'Route corridor',
            datetime: pt.datetime,
          });
        }
      }
    }

    // 2. Also match historical accidents from accidentLayer that lie within 300m of this route
    if (accidentLayer?.features?.length) {
      const THRESHOLD_M = 300;
      for (const f of accidentLayer.features) {
        const coords = f.geometry?.coordinates;
        if (!coords) continue;
        const [lng, lat] = coords;
        const p = f.properties || {};

        if (severityFilter === 'SEVERE_FATAL' && !['FATAL', 'SEVERE', 'CRITICAL', 'HIGH'].includes((p.severity || '').toUpperCase())) {
          continue;
        }
        if (severityFilter === 'MODERATE_MINOR' && !['MODERATE', 'MEDIUM', 'MINOR'].includes((p.severity || '').toUpperCase())) {
          continue;
        }

        const isNear = routeGeometry.some(([rlat, rlng]) => haversineMeters(lat, lng, rlat, rlng) < THRESHOLD_M);
        if (isNear) {
          const key = `${lat.toFixed(4)},${lng.toFixed(4)}`;
          if (!seen.has(key)) {
            seen.add(key);
            points.push({
              id: f.id || p.accident_id || key,
              lat,
              lng,
              type: 'historical',
              severity: p.severity || 'MODERATE',
              title: `${p.road_name || 'Route segment'}: ${p.severity || 'Incident'}`,
              description: p.description || 'Historical accident incident recorded along this route.',
              road_name: p.road_name,
              fatalities: p.fatalities,
              injuries: p.injuries,
              datetime: p.accident_time,
            });
          }
        }
      }
    }

    // 3. Fallback: If model predicts elevated accident risk (MEDIUM/HIGH/SEVERE/CRITICAL)
    // but no specific point was returned, plot a predicted risk zone pin at the route's midpoint
    if (points.length === 0 && routeAccidentRisk && routeGeometry.length >= 2) {
      const midIdx = Math.floor(routeGeometry.length / 2);
      const [midLat, midLng] = routeGeometry[midIdx];
      points.push({
        id: `route-midpoint-risk-${midLat.toFixed(4)}-${midLng.toFixed(4)}`,
        lat: midLat,
        lng: midLng,
        type: 'predicted_risk_zone',
        severity: routeAccidentRisk.risk_level || 'LOW',
        risk_percentage: routeAccidentRisk.risk_percentage,
        title: `AI Predicted Accident Risk: ${routeAccidentRisk.risk_level}`,
        description: `Predicted accident risk (${routeAccidentRisk.risk_percentage || 0}%) for this corridor under current road and weather conditions.`,
        road_name: routeAccidentRisk.road_name || routeTraffic?.road_name || 'Selected Route',
      });
    }

    return points;
  }, [routeGeometry, routeAccidentRisk, routeTraffic, accidentLayer, severityFilter]);

  // Worst congestion tier actually present on the route, for a summary badge.
  const worstRouteCongestion = useMemo(() => {
    if (!routeCongestionSegments) return null;
    const order = ['LOW', 'MEDIUM', 'HIGH', 'SEVERE'];
    let worst = null;
    for (const seg of routeCongestionSegments) {
      if (order.indexOf(seg.congestion) > order.indexOf(worst)) worst = seg.congestion;
    }
    return worst;
  }, [routeCongestionSegments]);

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



        {/* ========================================================= */}
        {/* Hotspots & Accident Predictions: Visible ONLY on selected direction */}
        {/* ========================================================= */}
        {routeGeometry && (
          <>
            {/* 1. Accident Hotspots on the Selected Direction */}
            {showRouteHotspots &&
              routeHotspots.map((f) => {
                const p = f.properties || {};
                const coords = f.geometry?.coordinates;
                if (!coords) return null;
                const [lng, lat] = coords;
                const color = p.color || '#EF4444';

                return (
                  <React.Fragment key={`route-hotspot-${f.id || p.hotspot_id || `${lat}-${lng}`}`}>
                    {/* Outer pulsating dashed hazard ring */}
                    <CircleMarker
                      center={[lat, lng]}
                      radius={20}
                      pathOptions={{
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.18,
                        weight: 2.5,
                        dashArray: '5, 5',
                      }}
                    />
                    {/* Inner hazard marker */}
                    <CircleMarker
                      center={[lat, lng]}
                      radius={8}
                      pathOptions={{
                        color: '#ffffff',
                        fillColor: color,
                        fillOpacity: 0.95,
                        weight: 2,
                      }}
                    >
                      <Tooltip sticky>
                        ⚠️ Accident Hotspot on Route: {p.road_name || 'Corridor'} ({p.risk_level || 'HIGH'} Risk)
                      </Tooltip>
                      <Popup>
                        <div className="space-y-1 text-xs text-asphalt-900 min-w-[210px]">
                          <div className="flex items-center justify-between gap-1.5 font-bold text-signal-red">
                            <span className="flex items-center gap-1">⚠️ Route Hotspot</span>
                            <span className="rounded px-1.5 py-0.5 text-[10px] font-bold text-white bg-signal-red uppercase">
                              {p.risk_level || 'HIGH'}
                            </span>
                          </div>
                          <p className="font-semibold text-slate-800">{p.road_name || 'Hazard Zone'}</p>
                          <div className="border-t border-slate-200 pt-1 text-[11px] text-slate-600 space-y-0.5">
                            <p><strong>Past Accidents Recorded:</strong> {p.accident_count || 1}</p>
                            {p.risk_score != null && <p><strong>Risk Score:</strong> {p.risk_score}</p>}
                            <p className="text-[10px] text-slate-400 mt-1">Identified hazard zone on your selected direction</p>
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  </React.Fragment>
                );
              })}

            {/* 2. Traffic Accident Predictions & Incident Points on Selected Direction */}
            {showRouteAccidents &&
              routeAccidents.map((pt) => {
                const isPredicted = pt.type === 'predicted_risk_zone';
                const markerColor = isPredicted
                  ? (pt.severity === 'CRITICAL' || pt.severity === 'SEVERE' ? '#DC2626' : (pt.severity === 'HIGH' ? '#EA580C' : '#F59E0B'))
                  : (SEVERITY_COLOR[pt.severity?.toUpperCase()] || '#DC2626');

                return (
                  <React.Fragment key={`route-acc-${pt.id}`}>
                    {isPredicted && (
                      <CircleMarker
                        center={[pt.lat, pt.lng]}
                        radius={18}
                        pathOptions={{
                          color: markerColor,
                          fillColor: markerColor,
                          fillOpacity: 0.22,
                          weight: 2,
                          dashArray: '3, 4',
                        }}
                      />
                    )}
                    <CircleMarker
                      center={[pt.lat, pt.lng]}
                      radius={isPredicted ? 8 : 6.5}
                      pathOptions={{
                        color: '#ffffff',
                        fillColor: markerColor,
                        fillOpacity: 1,
                        weight: 2,
                      }}
                    >
                      <Tooltip sticky>
                        {isPredicted
                          ? `🛡️ AI Accident Risk: ${pt.risk_percentage != null ? `${Math.round(pt.risk_percentage)}% ` : ''}(${pt.severity})`
                          : `⚠️ Incident: ${pt.severity} (${pt.road_name || 'Route'})`}
                      </Tooltip>
                      <Popup>
                        <div className="space-y-1 text-xs text-asphalt-900 min-w-[220px]">
                          <div className="flex items-center justify-between gap-1.5">
                            <span className="font-bold text-sm text-slate-900 flex items-center gap-1">
                              {isPredicted ? '🛡️ Accident Prediction' : '⚠️ Route Incident'}
                            </span>
                            <span
                              className="rounded px-1.5 py-0.5 text-[10px] font-bold text-white uppercase"
                              style={{ backgroundColor: markerColor }}
                            >
                              {pt.severity}
                            </span>
                          </div>
                          <p className="font-semibold text-slate-800">{pt.road_name || 'Route Point'}</p>
                          <div className="border-t border-slate-200 pt-1 text-[11px] text-slate-700 space-y-0.5">
                            {isPredicted ? (
                              <>
                                {pt.risk_percentage != null && (
                                  <p><strong>Predicted Incident Probability:</strong> <span className="font-bold text-signal-red">{Math.round(pt.risk_percentage)}%</span></p>
                                )}
                                <p className="text-slate-500 italic mt-1">{pt.description}</p>
                              </>
                            ) : (
                              <>
                                {(pt.fatalities != null || pt.injuries != null) && (
                                  <p><strong>Casualties:</strong> {pt.fatalities || 0} fatal - {pt.injuries || 0} injured</p>
                                )}
                                {pt.datetime && (
                                  <p className="text-slate-500"><strong>Recorded:</strong> {new Date(pt.datetime).toLocaleDateString()}</p>
                                )}
                                {pt.description && <p className="text-slate-500 italic mt-0.5">"{pt.description}"</p>}
                              </>
                            )}
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  </React.Fragment>
                );
              })}
          </>
        )}




        {/* Route: a dark "casing" line always underneath (so the route is
            unmistakable against busy map tiles, exactly like Google Maps'
            bordered route line), with congestion-colored segments drawn on
            top of it. Falls back to plain blue-on-casing if no traffic data
            can be matched to the route yet. */}
        {routeGeometry && routeGeometry.length > 1 && (
          <>
            {/* Casing: wide dark outline drawn first, underneath everything */}
            <Polyline
              positions={routeGeometry}
              pathOptions={{
                color: '#1F2937',
                weight: 11,
                opacity: 0.55,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            {showRouteTraffic && routeCongestionSegments
              ? routeCongestionSegments.map((seg, i) => (
                  <Polyline
                    key={i}
                    positions={seg.positions}
                    pathOptions={{
                      color: seg.color,
                      weight: 7,
                      opacity: 1,
                      lineCap: 'round',
                      lineJoin: 'round',
                    }}
                  >
                    <Tooltip sticky>
                      <div className="p-0.5 text-xs leading-snug">
                        <div className="flex items-center gap-1.5 font-bold">
                          <span
                            className="h-2 w-2 rounded-full inline-block"
                            style={{ backgroundColor: seg.color }}
                          />
                          {seg.congestion} Congestion
                        </div>
                        {seg.roadName && (
                          <div className="mt-0.5 font-medium text-slate-700">{seg.roadName}</div>
                        )}
                        <div className="mt-1 text-[11px] text-slate-500">
                          🕒 Prediction Time: {formatClockTime(resolvedTargetDate)}
                          {routeTraffic?.estimated_time ? ` (${routeTraffic.estimated_time})` : ''}
                        </div>
                        {(routeTraffic?.previous_records?.average_speed || routeTraffic?.previous_traffic?.average_speed) && (
                          <div className="text-[11px] text-slate-500">
                            🚗 Predicted Speed: {Math.round(routeTraffic.previous_records?.average_speed || routeTraffic.previous_traffic?.average_speed)} km/h
                          </div>
                        )}
                      </div>
                    </Tooltip>
                  </Polyline>
                ))
              : (
                <Polyline
                  positions={routeGeometry}
                  pathOptions={{
                    color: showRouteTraffic
                      ? (ROUTE_CONGESTION_COLOR[routeTraffic?.congestion_level || 'LOW'] || '#10B981')
                      : '#3B82F6',
                    weight: 7,
                    opacity: 1,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                >
                  <Tooltip sticky>
                    <div className="p-0.5 text-xs leading-snug">
                      <div className="flex items-center gap-1.5 font-bold">
                        <span
                          className="h-2 w-2 rounded-full inline-block"
                          style={{
                            backgroundColor: showRouteTraffic
                              ? (ROUTE_CONGESTION_COLOR[routeTraffic?.congestion_level || 'LOW'] || '#10B981')
                              : '#3B82F6',
                          }}
                        />
                        {showRouteTraffic ? `${routeTraffic?.congestion_level || 'LOW'} Congestion` : 'Selected Route'}
                      </div>
                      {routeTraffic?.road_name && (
                        <div className="mt-0.5 font-medium text-slate-700">{routeTraffic.road_name}</div>
                      )}
                      <div className="mt-1 text-[11px] text-slate-500">
                        🕒 Prediction Time: {formatClockTime(resolvedTargetDate)}
                        {routeTraffic?.estimated_time ? ` (${routeTraffic.estimated_time})` : ''}
                      </div>
                      {(routeTraffic?.previous_records?.average_speed || routeTraffic?.previous_traffic?.average_speed) && (
                        <div className="text-[11px] text-slate-500">
                          🚗 Predicted Speed: {Math.round(routeTraffic.previous_records?.average_speed || routeTraffic.previous_traffic?.average_speed)} km/h
                        </div>
                      )}
                    </div>
                  </Tooltip>
                </Polyline>
              )}
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
      {/* Floating Route Prediction Time & Traffic Pill over the Map */}
      {/* ------------------------------------------------------------- */}
      {routeGeometry && (
        <div className="absolute top-3 left-3 sm:left-[400px] z-[999] flex max-w-[calc(100vw-30px)] sm:max-w-[calc(100vw-420px)] flex-wrap items-center justify-between gap-2.5 rounded-xl border border-slate-200/90 bg-white/95 px-3.5 py-2 text-xs shadow-xl backdrop-blur-md dark:border-asphalt-700/90 dark:bg-asphalt-900/95">
          <div className="flex flex-wrap items-center gap-2.5 min-w-0">
            <div className="flex items-center gap-1.5 font-bold">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: ROUTE_CONGESTION_COLOR[routeTraffic?.congestion_level || 'LOW'] || '#10B981' }}
              />
              <span className="text-slate-900 dark:text-asphalt-100">
                {routeTraffic?.congestion_level || 'LOW'} Congestion
              </span>
            </div>

            <span className="hidden sm:inline-block h-3 w-px bg-slate-200 dark:bg-asphalt-700" />

            <div className="flex items-center gap-1 text-slate-700 dark:text-asphalt-200 font-medium">
              <span>🕒 Target:</span>
              <span className="font-bold text-signal-blue">
                {formatClockTime(resolvedTargetDate)}
              </span>
              {routeTraffic?.estimated_time && (
                <span className="text-[11px] text-slate-400 dark:text-asphalt-400">
                  ({routeTraffic.estimated_time})
                </span>
              )}
            </div>

            {routeInfo?.duration_minutes && (
              <>
                <span className="hidden md:inline-block h-3 w-px bg-slate-200 dark:bg-asphalt-700" />
                <div className="text-slate-600 dark:text-asphalt-300">
                  🏁 Arrival: <span className="font-semibold text-slate-900 dark:text-asphalt-100">~{formatClockTime(estimatedArrivalTime)}</span> ({routeInfo.duration_minutes}m)
                </div>
              </>
            )}

            {(routeTraffic?.previous_records?.average_speed || routeTraffic?.previous_traffic?.average_speed) && (
              <>
                <span className="hidden md:inline-block h-3 w-px bg-slate-200 dark:bg-asphalt-700" />
                <div className="text-slate-600 dark:text-asphalt-300">
                  🚗 Flow: <span className="font-semibold">{Math.round(routeTraffic.previous_records?.average_speed || routeTraffic.previous_traffic?.average_speed)} km/h</span>
                </div>
              </>
            )}

            {routeAccidentRisk && (
              <>
                <span className="hidden lg:inline-block h-3 w-px bg-slate-200 dark:bg-asphalt-700" />
                <div className="flex items-center gap-1 text-slate-700 dark:text-asphalt-300">
                  <span>🛡️ Risk:</span>
                  <span className="font-semibold text-signal-red">
                    {routeAccidentRisk.risk_level}
                    {routeAccidentRisk.risk_percentage != null && ` (${Math.round(routeAccidentRisk.risk_percentage)}%)`}
                  </span>
                </div>
              </>
            )}

            {routeHotspots.length > 0 && (
              <>
                <span className="hidden xl:inline-block h-3 w-px bg-slate-200 dark:bg-asphalt-700" />
                <div className="inline-flex items-center gap-1 rounded-full bg-signal-red/10 px-2 py-0.5 text-[11px] font-semibold text-signal-red">
                  ⚠️ {routeHotspots.length} Hotspot{routeHotspots.length > 1 ? 's' : ''} on direction
                </div>
              </>
            )}
          </div>

          {/* Quick Time Switcher on Map */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-[10px] uppercase font-semibold text-slate-400 dark:text-asphalt-500 mr-0.5">Test:</span>
            {[
              { id: 'now', label: 'Now' },
              { id: '30m', label: '+30m' },
              { id: '1h', label: '+1h' },
              { id: 'peak_evening', label: '6 PM' },
            ].map((btn) => (
              <button
                key={btn.id}
                type="button"
                onClick={() => handleDepartureOptionSelect(btn.id)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                  departureOption === btn.id
                    ? 'bg-signal-blue text-white shadow-xs'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-asphalt-800 dark:hover:bg-asphalt-700 dark:text-asphalt-200'
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Floating Search / Directions panel - top-left, Google-Maps-style */}
      {/* ------------------------------------------------------------- */}
      <div className="absolute left-3 top-3 z-[1000] w-[min(92vw,380px)]">
        <div className="max-h-[85vh] overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
          <div className="px-2 pt-2">
            <VoiceAssistant
              compact
              onRoute={handleVoiceRoute}
              disabled={voiceBusy || routeLoading}
              hint="Try: “Directions from Uppal to Nagole”"
            />
          </div>

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
                  placeholder="Search Metrivon Maps"
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
                <ul className="mt-1 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl dark:border-asphalt-700 dark:bg-asphalt-900 divide-y divide-slate-100 dark:divide-asphalt-800">
                  {searchSuggestions.map((s, i) => {
                    const meta = getCategoryBadge(s.category);
                    return (
                      <li
                        key={i}
                        onMouseDown={() => selectSuggestion('search', s)}
                        className="flex items-start gap-2.5 cursor-pointer px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-asphalt-800 transition-colors"
                      >
                        <span className="text-base select-none mt-0.5">{meta.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-semibold text-slate-900 dark:text-asphalt-100 truncate">
                              {s.primary_name || s.display_name}
                            </span>
                            {s.category && s.category !== 'location' && (
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${meta.color}`}>
                                {meta.badge}
                              </span>
                            )}
                          </div>
                          {s.secondary_name && (
                            <p className="text-[11px] text-slate-500 dark:text-asphalt-400 truncate mt-0.5">
                              {s.secondary_name}
                            </p>
                          )}
                        </div>
                      </li>
                    );
                  })}
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
                      <ul className="absolute left-0 right-0 top-full z-[1100] mt-1 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl dark:border-asphalt-700 dark:bg-asphalt-900 divide-y divide-slate-100 dark:divide-asphalt-800">
                        {startSuggestions.map((s, i) => {
                          const meta = getCategoryBadge(s.category);
                          return (
                            <li
                              key={i}
                              onMouseDown={() => selectSuggestion('start', s)}
                              className="flex items-start gap-2.5 cursor-pointer px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-asphalt-800 transition-colors"
                            >
                              <span className="text-base select-none mt-0.5">{meta.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="font-semibold text-slate-900 dark:text-asphalt-100 truncate">
                                    {s.primary_name || s.display_name}
                                  </span>
                                  {s.category && s.category !== 'location' && (
                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${meta.color}`}>
                                      {meta.badge}
                                    </span>
                                  )}
                                </div>
                                {s.secondary_name && (
                                  <p className="text-[11px] text-slate-500 dark:text-asphalt-400 truncate mt-0.5">
                                    {s.secondary_name}
                                  </p>
                                )}
                              </div>
                            </li>
                          );
                        })}
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
                      <ul className="absolute left-0 right-0 top-full z-[1100] mt-1 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl dark:border-asphalt-700 dark:bg-asphalt-900 divide-y divide-slate-100 dark:divide-asphalt-800">
                        {endSuggestions.map((s, i) => {
                          const meta = getCategoryBadge(s.category);
                          return (
                            <li
                              key={i}
                              onMouseDown={() => selectSuggestion('end', s)}
                              className="flex items-start gap-2.5 cursor-pointer px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-asphalt-800 transition-colors"
                            >
                              <span className="text-base select-none mt-0.5">{meta.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="font-semibold text-slate-900 dark:text-asphalt-100 truncate">
                                    {s.primary_name || s.display_name}
                                  </span>
                                  {s.category && s.category !== 'location' && (
                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${meta.color}`}>
                                      {meta.badge}
                                    </span>
                                  )}
                                </div>
                                {s.secondary_name && (
                                  <p className="text-[11px] text-slate-500 dark:text-asphalt-400 truncate mt-0.5">
                                    {s.secondary_name}
                                  </p>
                                )}
                              </div>
                            </li>
                          );
                        })}
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

              {/* ----------------------------------------------------------- */}
              {/* Prediction & Departure Time Controls (Present by default)    */}
              {/* ----------------------------------------------------------- */}
              <div className="mt-2.5 rounded-lg border border-slate-200/90 bg-slate-50/80 p-2.5 dark:border-asphalt-700 dark:bg-asphalt-800/60">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-900 dark:text-asphalt-100">
                    <span>🕒</span> Departure / Prediction Time
                  </span>
                  <span className="text-[11px] font-bold text-signal-blue">
                    {departureOption === 'now'
                      ? `Now (${formatClockTime(resolvedTargetDate)})`
                      : departureOption === '30m'
                      ? `+30m (${formatClockTime(resolvedTargetDate)})`
                      : departureOption === '15m'
                      ? `+15m (${formatClockTime(resolvedTargetDate)})`
                      : departureOption === '1h'
                      ? `+1h (${formatClockTime(resolvedTargetDate)})`
                      : departureOption === 'peak_evening'
                      ? '6:00 PM (Peak)'
                      : departureOption === 'peak_morning'
                      ? '9:00 AM (Peak)'
                      : `Custom (${formatClockTime(resolvedTargetDate)})`}
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {[
                    { id: 'now', label: '⚡ Now' },
                    { id: '15m', label: '+15m' },
                    { id: '30m', label: '+30m' },
                    { id: '1h', label: '+1h' },
                    { id: 'peak_evening', label: '🌆 6 PM' },
                    { id: 'peak_morning', label: '🌅 9 AM' },
                    { id: 'custom', label: '🕒 Custom' },
                  ].map((chip) => {
                    const isActive = departureOption === chip.id;
                    return (
                      <button
                        key={chip.id}
                        type="button"
                        onClick={() => handleDepartureOptionSelect(chip.id)}
                        className={`rounded-md px-2 py-1 text-[11px] font-medium transition-all ${
                          isActive
                            ? 'bg-signal-blue text-white shadow-xs font-semibold'
                            : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 dark:border-asphalt-700 dark:bg-asphalt-800 dark:text-asphalt-200 dark:hover:bg-asphalt-700'
                        }`}
                      >
                        {chip.label}
                      </button>
                    );
                  })}
                </div>

                {departureOption === 'custom' && (
                  <div className="mt-2 flex items-center gap-2">
                    <label className="text-[11px] font-medium text-slate-500 dark:text-asphalt-400">Select target time:</label>
                    <input
                      type="time"
                      value={customTime}
                      onChange={(e) => handleCustomTimeChange(e.target.value)}
                      className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs text-slate-800 outline-none focus:border-signal-blue dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-100"
                    />
                  </div>
                )}

                <p className="mt-1.5 text-[10px] text-slate-500 dark:text-asphalt-400">
                  By default active (+30m). Select any time to check if predicted traffic & congestion are accurate for that hour.
                </p>
              </div>

              <div className="flex items-center justify-between px-1 pt-2">
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

                  {/* Time & Traffic Prediction Summary Breakdown */}
                  <div className="mt-2 rounded-lg border border-slate-200/90 bg-slate-50 p-2.5 text-xs dark:border-asphalt-700 dark:bg-asphalt-800/70">
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div>
                        <span className="block text-[10px] font-semibold uppercase text-slate-400 dark:text-asphalt-400">
                          Departure Time
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-asphalt-100 flex items-center gap-1">
                          🕒 {formatClockTime(resolvedTargetDate)}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] font-semibold uppercase text-slate-400 dark:text-asphalt-400">
                          Estimated Arrival
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-asphalt-100 flex items-center gap-1">
                          🏁 {formatClockTime(estimatedArrivalTime)}
                        </span>
                      </div>
                    </div>

                    {routeTraffic?.estimated_time && (
                      <div className="mt-1.5 pt-1.5 border-t border-slate-200/70 dark:border-asphalt-700 text-[11px] flex items-center justify-between text-slate-600 dark:text-asphalt-300">
                        <span>Traffic Window:</span>
                        <span className="font-semibold text-slate-900 dark:text-asphalt-100">
                          {routeTraffic.estimated_time}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-2 flex flex-wrap gap-1.5 px-1">
                    {predictionsLoading && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-signal-blue animate-pulse">
                        <span className="h-1.5 w-1.5 rounded-full bg-signal-blue animate-ping" />
                        Predicting traffic for {formatClockTime(resolvedTargetDate)}...
                      </span>
                    )}
                    {(worstRouteCongestion || routeTraffic?.congestion_level) && (
                      <span
                        className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold text-white shadow-sm"
                        style={{ backgroundColor: ROUTE_CONGESTION_COLOR[worstRouteCongestion || routeTraffic?.congestion_level] || '#10B981' }}
                      >
                        ● Traffic: {worstRouteCongestion || routeTraffic?.congestion_level}
                        {(routeTraffic?.previous_records?.average_speed || routeTraffic?.previous_traffic?.average_speed) &&
                          ` (${Math.round(routeTraffic.previous_records?.average_speed || routeTraffic.previous_traffic?.average_speed)} km/h)`}
                      </span>
                    )}
                    {routeAccidentRisk && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-signal-red/40 bg-signal-red/10 px-2.5 py-0.5 text-[11px] font-medium text-signal-red">
                        🛡️ Accident risk: {routeAccidentRisk.risk_level}
                        {routeAccidentRisk.risk_percentage != null
                          ? ` (${Number(routeAccidentRisk.risk_percentage).toFixed(0)}%)`
                          : ''}
                      </span>
                    )}
                    {routeHotspots.length > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-signal-amber/40 bg-signal-amber/10 px-2.5 py-0.5 text-[11px] font-semibold text-signal-amber">
                        ⚠️ {routeHotspots.length} Hotspot{routeHotspots.length > 1 ? 's' : ''} on direction
                      </span>
                    )}
                  </div>

                  {!isNavigating ? (
                    <button
                      onClick={startNavigation}
                      disabled={!routeInfo.steps?.length}
                      className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-signal-blue px-3 py-2 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
                    >
                      ▶ Start
                    </button>
                  ) : (
                    <button
                      onClick={stopNavigation}
                      className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-signal-red px-3 py-2 text-sm font-semibold text-signal-red transition-colors hover:bg-signal-red/10"
                    >
                      ■ End navigation
                    </button>
                  )}
                  {navError && <p className="mt-1 text-xs text-signal-red">{navError}</p>}

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
                          {routeInfo.steps.map((step, i) => {
                            const isCurrent = isNavigating && i === currentStepIndex;
                            return (
                              <li key={i}>
                                <button
                                  onClick={() => step.coordinates && setFlyTarget(step.coordinates)}
                                  className={`flex w-full items-start gap-2 rounded-md px-1.5 py-1.5 text-left text-xs transition-colors hover:bg-slate-100 dark:hover:bg-asphalt-800 ${
                                    isCurrent ? 'bg-signal-blue/10 ring-1 ring-signal-blue/40' : ''
                                  }`}
                                >
                                  <span
                                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] ${
                                      isCurrent
                                        ? 'bg-signal-blue text-white'
                                        : 'bg-slate-100 dark:bg-asphalt-800'
                                    }`}
                                  >
                                    {stepGlyph(step)}
                                  </span>
                                  <span className={`flex-1 ${isCurrent ? 'font-semibold text-slate-900 dark:text-asphalt-100' : 'text-slate-700 dark:text-asphalt-200'}`}>
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
                            );
                          })}
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
          <div className="mb-2 w-72 rounded-xl border border-slate-200 bg-white p-3.5 text-xs shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
            <div className="mb-2.5 flex items-center justify-between">
              <div>
                <p className="font-bold text-slate-900 dark:text-asphalt-100">
                  {routeGeometry ? 'Route-Specific Layers' : 'Map Layers'}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-asphalt-400">
                  {routeGeometry ? 'Overlays along selected direction' : 'Clean map view'}
                </p>
              </div>
              <button
                onClick={() => setLayersOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-asphalt-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {routeGeometry ? (
              <div className="space-y-1.5">
                <label className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-asphalt-800 cursor-pointer transition-colors">
                  <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200 font-medium">
                    <span className="h-2.5 w-2.5 rounded-full bg-signal-amber" />
                    <span>Route Traffic Flow</span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded accent-signal-blue cursor-pointer"
                    checked={showRouteTraffic}
                    onChange={() => setShowRouteTraffic((v) => !v)}
                  />
                </label>

                <label className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-asphalt-800 cursor-pointer transition-colors">
                  <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200 font-medium">
                    <span className="h-2.5 w-2.5 rounded-full bg-signal-red" />
                    <span>Accident Predictions ({routeAccidents.length})</span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded accent-signal-blue cursor-pointer"
                    checked={showRouteAccidents}
                    onChange={() => setShowRouteAccidents((v) => !v)}
                  />
                </label>

                <label className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-asphalt-800 cursor-pointer transition-colors">
                  <span className="flex items-center gap-2 text-slate-700 dark:text-asphalt-200 font-medium">
                    <span className="h-2.5 w-2.5 rounded-full bg-orange-500" />
                    <span>Route Hotspots ({routeHotspots.length})</span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded accent-signal-blue cursor-pointer"
                    checked={showRouteHotspots}
                    onChange={() => setShowRouteHotspots((v) => !v)}
                  />
                </label>

                <div className="mt-2 flex items-center gap-1.5 border-t border-slate-200 pt-2 dark:border-asphalt-800">
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
              </div>
            ) : (
              <div className="py-2 text-[11px] text-slate-500 dark:text-asphalt-400 space-y-1.5">
                <p>
                  To keep the map clean and responsive, traffic flow, accident predictions, and hazard hotspots appear <strong>only along your selected route</strong>.
                </p>
                <p className="font-semibold text-signal-blue">
                  👉 Search a destination or click "Get Directions" to activate route overlays.
                </p>
              </div>
            )}

            <div className="mt-2.5 flex items-center justify-between border-t border-slate-200 pt-2 dark:border-asphalt-800 text-[11px]">
              <span className="text-slate-400 dark:text-asphalt-500">
                {lastUpdated ? `Synced ${lastUpdated}` : 'Live'}
              </span>
              <button
                onClick={loadMapData}
                className="rounded bg-slate-100 px-2 py-1 font-medium text-slate-700 hover:bg-slate-200 dark:bg-asphalt-800 dark:text-asphalt-200 dark:hover:bg-asphalt-700"
              >
                Refresh
              </button>
            </div>
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
          <div className="border-t border-slate-200 p-3 text-xs dark:border-asphalt-800">
            <p className="mb-1.5 font-semibold text-slate-700 dark:text-asphalt-200">Route traffic</p>
            <div className="mb-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5">
              <LegendItem color={ROUTE_CONGESTION_COLOR.LOW} label="Low - clear" line />
              <LegendItem color={ROUTE_CONGESTION_COLOR.MEDIUM} label="Medium" line />
              <LegendItem color={ROUTE_CONGESTION_COLOR.HIGH} label="High / Severe" line />
            </div>
            <p className="mb-1.5 border-t border-slate-200 pt-2 font-semibold text-slate-700 dark:border-asphalt-800 dark:text-asphalt-200">
              Roads &amp; incidents
            </p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
              <LegendItem color={CONGESTION_COLOR.LOW} label="Low Traffic (<40%)" line />
              <LegendItem color={CONGESTION_COLOR.MEDIUM} label="Medium Traffic" line />
              <LegendItem color={CONGESTION_COLOR.HIGH} label="High Congestion" line />
              <LegendItem color={CONGESTION_COLOR.SEVERE} label="Severe (>85%)" line />
              <LegendItem color={SEVERITY_COLOR.FATAL} label="Fatal Accident" dot />
              <LegendItem color={SEVERITY_COLOR.SEVERE} label="Severe Accident" dot />
              <LegendItem color={SEVERITY_COLOR.MODERATE} label="Moderate Incident" dot />
              <LegendItem color={SEVERITY_COLOR.MINOR} label="Minor Incident" dot />
              <LegendItem color="#A855F7" label="Traffic Anomaly" dot />
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Live navigation banner - Google-Maps-style, shown while "Start" */}
      {/* turn-by-turn tracking is active (real GPS via watchPosition)    */}
      {/* ------------------------------------------------------------- */}
      {isNavigating && routeInfo?.steps?.length > 0 && (
        <div className="absolute inset-x-3 bottom-3 z-[1100] mx-auto max-w-md rounded-xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-signal-blue text-xl text-white">
              {stepGlyph(routeInfo.steps[currentStepIndex] || routeInfo.steps[0])}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-base font-bold text-slate-900 dark:text-asphalt-100">
                {(routeInfo.steps[currentStepIndex] || routeInfo.steps[0]).instruction}
              </p>
              <p className="text-xs text-slate-500 dark:text-asphalt-400">
                Step {currentStepIndex + 1} of {routeInfo.steps.length}
                {(routeInfo.steps[currentStepIndex]?.distance_meters ?? 0) > 0 &&
                  ` · ${
                    routeInfo.steps[currentStepIndex].distance_meters >= 1000
                      ? `${(routeInfo.steps[currentStepIndex].distance_meters / 1000).toFixed(1)} km`
                      : `${Math.round(routeInfo.steps[currentStepIndex].distance_meters)} m`
                  }`}
              </p>
            </div>
            <button
              onClick={stopNavigation}
              className="shrink-0 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-signal-red/50 hover:text-signal-red dark:border-asphalt-700 dark:text-asphalt-300"
            >
              End
            </button>
          </div>
          {navError && <p className="mt-2 text-xs text-signal-red">{navError}</p>}
        </div>
      )}
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