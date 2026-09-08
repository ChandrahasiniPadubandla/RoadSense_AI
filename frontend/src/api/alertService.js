import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { mockAlerts, mockRoads } from '../mock/mockData';

function fakeDelay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let localAlerts = [...mockAlerts];

function mapAlert(row, roadNameById) {
  return {
    id: row.alert_id,
    roadId: row.road_id != null ? String(row.road_id) : null,
    roadName: roadNameById[row.road_id] || (row.road_id ? `Road ${row.road_id}` : '—'),
    predictionId: row.prediction_id,
    type: row.alert_type,
    severity: row.severity,
    message: row.message,
    createdAt: row.created_at,
    // components use a boolean today; the DB models this as a status enum
    // ('ACTIVE' | 'RESOLVED' | ...) so we translate both ways.
    acknowledged: row.status !== 'ACTIVE',
    status: row.status,
    resolvedAt: row.resolved_at,
  };
}

/** GET /alerts */
export async function getAlerts() {
  const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return localAlerts.map((a) => mapAlert(a, roadNameById));
  }
  const { data } = await axiosClient.get('/alerts');
  return data.map((a) => mapAlert(a, roadNameById));
}

/**
 * PATCH /alerts/:id  body: { status: 'RESOLVED', resolved_at: <now> }
 * (there's no dedicated "acknowledge" column in the schema — status +
 * resolved_at on the alerts table cover it; adjust the body below if your
 * backend adds a separate acknowledged_at/acknowledged_by column instead.)
 */
export async function acknowledgeAlert(id) {
  const roadNameById = Object.fromEntries(mockRoads.map((r) => [r.road_id, r.road_name]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    localAlerts = localAlerts.map((a) =>
      a.alert_id === id
        ? { ...a, status: 'RESOLVED', resolved_at: new Date().toISOString() }
        : a
    );
    return mapAlert(localAlerts.find((a) => a.alert_id === id), roadNameById);
  }
  const { data } = await axiosClient.patch(`/alerts/${id}`, {
    status: 'RESOLVED',
    resolved_at: new Date().toISOString(),
  });
  return mapAlert(data, roadNameById);
}
