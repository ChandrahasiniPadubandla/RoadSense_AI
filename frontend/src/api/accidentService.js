import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { parseGeoPoint, toGeoPoint } from '../utils/geo';
import {
  mockAccidents,
  mockAccidentPredictions,
  mockHotspots,
  mockRoads,
} from '../mock/mockData';

function fakeDelay(ms = 350) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let localAccidents = [...mockAccidents]; // lets the mock "create" work in-session

// -----------------------------------------------------------------------
// Mapping layer: accidents / accident_predictions / accident_hotspots
// columns -> the shape src/pages/Accident*.jsx already expects.
// -----------------------------------------------------------------------

function mapAccident(row, roadNameById) {
  const point = parseGeoPoint(row.location);
  const dt = row.accident_datetime ? new Date(row.accident_datetime) : null;
  return {
    id: `A-${row.accident_id}`,
    roadId: row.road_id != null ? String(row.road_id) : null,
    roadName: roadNameById?.[row.road_id],
    location: row.road_id && roadNameById?.[row.road_id]
      ? roadNameById[row.road_id]
      : `Lat ${point?.lat?.toFixed(4)}, Lng ${point?.lng?.toFixed(4)}`,
    lat: point?.lat,
    lng: point?.lng,
    date: dt ? dt.toISOString().slice(0, 10) : '',
    time: dt ? dt.toTimeString().slice(0, 5) : '',
    weather: row.weather_condition,
    roadCondition: row.road_condition,
    vehicleCount: row.number_of_vehicles ?? row.vehicle_count,
    severity: row.severity,
    fatalities: row.fatalities,
    injuries: row.injuries,
    description: row.description,
    createdBy: row.created_by,
  };
}

function mapRiskPrediction(row, roadNameById) {
  return {
    roadId: String(row.road_id),
    roadName: roadNameById[row.road_id] || `Road ${row.road_id}`,
    riskPercent: Math.round(row.risk_percentage),
    riskLevel: row.risk_level,
    confidence: row.confidence_score,
    // The DB doesn't store the individual contributing factors on this table —
    // if you want the factor breakdown shown today, either have the ML
    // service return them alongside the prediction, or fetch the road's
    // latest traffic_records/weather_records row and merge here.
    factors: row.factors || null,
  };
}

function mapHotspot(row) {
  const point = parseGeoPoint(row.location);
  return {
    id: `H-${row.hotspot_id}`,
    zoneId: row.zone_id,
    location: `Lat ${point?.lat?.toFixed(4)}, Lng ${point?.lng?.toFixed(4)}`,
    lat: point?.lat,
    lng: point?.lng,
    accidentCount: row.accident_count,
    riskLevel: row.risk_level,
    riskScore: row.risk_score,
  };
}

// -----------------------------------------------------------------------
// Public API
// -----------------------------------------------------------------------

/** GET /accidents */
export async function getAccidents() {
  const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return localAccidents.map((a) => mapAccident(a, roadNameById));
  }
  const { data } = await axiosClient.get('/accidents');
  return data.map((a) => mapAccident(a, roadNameById));
}

/**
 * POST /accidents
 * body must match the accidents table: road_id, location (GeoJSON Point),
 * accident_datetime, weather_condition, road_condition, vehicle_count,
 * number_of_vehicles, severity, fatalities, injuries, description
 */
export async function createAccident(payload) {
  const body = {
    road_id: payload.roadId ? Number(payload.roadId) : null,
    location: payload.lat != null ? toGeoPoint(payload.lat, payload.lng) : null,
    accident_datetime: `${payload.date}T${payload.time}:00Z`,
    weather_condition: payload.weather,
    road_condition: payload.roadCondition,
    vehicle_count: payload.vehicleCount,
    number_of_vehicles: payload.vehicleCount,
    severity: payload.severity,
    fatalities: payload.fatalities,
    injuries: payload.injuries,
    description: payload.description,
  };

  if (USE_MOCK_DATA) {
    await fakeDelay();
    const newRow = { accident_id: Date.now(), ...body, created_by: null };
    localAccidents = [newRow, ...localAccidents];
    const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
    return mapAccident(newRow, roadNameById);
  }

  const { data } = await axiosClient.post('/accidents', body);
  return mapAccident(data, {});
}

/** GET /accidents/hotspots */
export async function getHotspots() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockHotspots.map(mapHotspot);
  }
  const { data } = await axiosClient.get('/accidents/hotspots');
  return data.map(mapHotspot);
}

/** GET /predictions/accident-risk */
export async function getRiskPredictions() {
  const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    // demo factor breakdown so the UI has something to show — see note above
    const withFactors = mockAccidentPredictions.map((p) => ({
      ...p,
      factors: {
        trafficDensity: p.road_id === 103 ? 'High' : 'Medium',
        avgSpeed: p.road_id === 103 ? 72 : 40,
        rainfall: p.road_id === 103 ? 'Heavy' : 'None',
        historicalAccidents: p.road_id === 103 ? 14 : 8,
      },
    }));
    return withFactors.map((p) => mapRiskPrediction(p, roadNameById));
  }
  const { data } = await axiosClient.get('/predictions/accident-risk');
  return data.map((p) => mapRiskPrediction(p, roadNameById));
}
