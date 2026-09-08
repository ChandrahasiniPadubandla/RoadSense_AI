import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { parseGeoPoint } from '../utils/geo';
import {
  mockRoads,
  mockLatestTrafficByRoad,
  mockTrafficPredictions,
  mockAnomalies,
  mockDashboardStats,
  mockTrafficHistory,
} from '../mock/mockData';

function fakeDelay(ms = 350) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// -----------------------------------------------------------------------
// Mapping layer: DB column names (roads, traffic_records, traffic_predictions,
// traffic_anomalies tables) -> the flat camelCase shape components use.
// If your backend's JSON already matches these DB names, these mappers are
// literally all that's needed to go live — nothing in src/pages/ changes.
// -----------------------------------------------------------------------

function mapRoad(road, latestTraffic) {
  const start = parseGeoPoint(road.start_location);
  return {
    id: String(road.road_id),
    zoneId: road.zone_id,
    name: road.road_name,
    roadType: road.road_type,
    capacity: road.road_capacity,
    speedLimit: road.speed_limit,
    lanes: road.number_of_lanes,
    isActive: road.is_active,
    lat: start?.lat,
    lng: start?.lng,
    // fields sourced from the most recent traffic_records row for this road
    vehicleCount: latestTraffic?.vehicle_count ?? null,
    avgSpeed: latestTraffic?.average_speed ?? null,
    trafficDensity: latestTraffic?.traffic_density ?? null,
    trafficLevel: latestTraffic?.congestion_level ?? 'LOW',
    weather: latestTraffic?.weather_condition ?? road.road_condition,
    updatedAt: latestTraffic?.timestamp ?? null,
  };
}

function mapPrediction(pred, roadNameById) {
  return {
    id: pred.prediction_id,
    roadId: String(pred.road_id),
    roadName: roadNameById[pred.road_id] || `Road ${pred.road_id}`,
    predictedLevel: pred.predicted_congestion,
    predictedVehicleCount: pred.predicted_vehicle_count,
    confidence: pred.confidence_score,
    targetTime: pred.target_time,
    // windowStart/End displayed as a single HH:MM for the table; adjust if
    // your model instead returns a start+end pair explicitly.
    windowStart: formatTime(pred.target_time),
    windowEnd: formatTime(addMinutes(pred.target_time, 60)),
  };
}

function mapAnomaly(anomaly, roadNameById) {
  return {
    id: anomaly.anomaly_id,
    roadId: String(anomaly.road_id),
    roadName: roadNameById[anomaly.road_id] || `Road ${anomaly.road_id}`,
    expected: anomaly.normal_vehicle_count,
    observed: anomaly.actual_vehicle_count,
    detectedAt: anomaly.detected_at,
    possibleCause: describeAnomalyType(anomaly.anomaly_type, anomaly.description),
  };
}

function describeAnomalyType(type, description) {
  const labels = {
    VOLUME_SPIKE: 'Sudden volume spike — possible accident, event, or closure',
    VOLUME_DROP: 'Sudden volume drop — possible road closure or diversion',
  };
  return description || labels[type] || type;
}

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function addMinutes(iso, minutes) {
  return new Date(new Date(iso).getTime() + minutes * 60000).toISOString();
}

// -----------------------------------------------------------------------
// Public API — pages import ONLY these functions, never axios directly.
// -----------------------------------------------------------------------

/** GET /roads (joined with each road's latest traffic_records row) */
export async function getRoads() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockRoads.map((r) => mapRoad(r, mockLatestTrafficByRoad[r.road_id]));
  }
  const { data } = await axiosClient.get('/roads');
  // Expected: array of { ...roads columns, latest_traffic: {...traffic_records columns} }
  return data.map((r) => mapRoad(r, r.latest_traffic));
}

/** GET /roads/:id */
export async function getRoadById(id) {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    const road = mockRoads.find((r) => String(r.road_id) === String(id));
    if (!road) throw new Error('Road not found');
    return mapRoad(road, mockLatestTrafficByRoad[road.road_id]);
  }
  const { data } = await axiosClient.get(`/roads/${id}`);
  return mapRoad(data, data.latest_traffic);
}

/** GET /predictions/traffic */
export async function getCongestionPredictions() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
    return mockTrafficPredictions.map((p) => mapPrediction(p, roadNameById));
  }
  // Ask backend to include road_name in the join, or fetch /roads separately
  // and build roadNameById the same way as the mock branch.
  const { data } = await axiosClient.get('/predictions/traffic');
  const roadNameById = Object.fromEntries(
    (data.roads || []).map((r) => [r.road_id, r.road_name])
  );
  return (data.predictions || data).map((p) => mapPrediction(p, roadNameById));
}

/** GET /anomalies/traffic */
export async function getAnomalies() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
    return mockAnomalies.map((a) => mapAnomaly(a, roadNameById));
  }
  const { data } = await axiosClient.get('/anomalies/traffic');
  const roadNameById = Object.fromEntries(
    (data.roads || []).map((r) => [r.road_id, r.road_name])
  );
  return (data.anomalies || data).map((a) => mapAnomaly(a, roadNameById));
}

/**
 * GET /dashboard/stats
 * This is a summary endpoint your backend should compute (e.g. COUNT queries
 * across roads/traffic_records/accidents/accident_hotspots) rather than the
 * frontend aggregating raw rows itself.
 */
export async function getDashboardStats() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockDashboardStats;
  }
  const { data } = await axiosClient.get('/dashboard/stats');
  return data; // { activeRoads, highTraffic, accidentAlerts, highRiskZones }
}

/** GET /traffic-records?road_id=&hours=24 -> hourly aggregation for the chart */
export async function getTrafficHistory(roadId) {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockTrafficHistory;
  }
  const { data } = await axiosClient.get('/traffic-records', {
    params: { road_id: roadId, hours: 24 },
  });
  // Expected: [{ hour: 'HH:MM', vehicles: number }, ...] — if the backend
  // instead returns raw traffic_records rows, aggregate here:
  // return data.map(r => ({ hour: formatTime(r.timestamp), vehicles: r.vehicle_count }));
  return data;
}
