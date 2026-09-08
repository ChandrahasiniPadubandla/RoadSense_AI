import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { parseGeoPoint, toGeoPoint } from '../utils/geo';
import { mockZones } from '../mock/mockData';

function fakeDelay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let localZones = [...mockZones];

function mapZone(row) {
  const point = parseGeoPoint(row.location);
  return {
    id: row.zone_id,
    name: row.zone_name,
    description: row.description,
    lat: point?.lat,
    lng: point?.lng,
  };
}

/** GET /zones */
export async function getZones() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return localZones.map(mapZone);
  }
  const { data } = await axiosClient.get('/zones');
  return data.map(mapZone);
}

/** POST /zones  body: { zone_name, description, location } */
export async function createZone(payload) {
  const body = {
    zone_name: payload.name,
    description: payload.description,
    location: payload.lat != null ? toGeoPoint(payload.lat, payload.lng) : null,
  };
  if (USE_MOCK_DATA) {
    await fakeDelay();
    const newRow = { zone_id: Date.now(), ...body };
    localZones = [newRow, ...localZones];
    return mapZone(newRow);
  }
  const { data } = await axiosClient.post('/zones', body);
  return mapZone(data);
}
