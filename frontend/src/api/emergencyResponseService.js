import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { mockEmergencyResponses, mockAccidents, mockUsers } from '../mock/mockData';

function fakeDelay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let localResponses = [...mockEmergencyResponses];

function mapResponse(row, accidentById, userById) {
  const accident = accidentById[row.accident_id];
  return {
    id: row.response_id,
    accidentId: row.accident_id,
    accidentLocation: accident ? `Accident A-${accident.accident_id}` : `Accident ${row.accident_id}`,
    assignedUserId: row.assigned_user_id,
    assignedUserName: userById[row.assigned_user_id]?.name || 'Unassigned',
    status: row.response_status, // PENDING | EN_ROUTE | ON_SCENE | RESOLVED
    assignedAt: row.assigned_at,
    arrivedAt: row.arrived_at,
    resolvedAt: row.resolved_at,
    notes: row.notes,
  };
}

/** GET /emergency-responses */
export async function getEmergencyResponses() {
  const accidentById = Object.fromEntries(mockAccidents.map((a) => [a.accident_id, a]));
  const userById = Object.fromEntries(mockUsers.map((u) => [u.user_id, u]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return localResponses.map((r) => mapResponse(r, accidentById, userById));
  }
  const { data } = await axiosClient.get('/emergency-responses');
  return data.map((r) => mapResponse(r, accidentById, userById));
}

/**
 * PATCH /emergency-responses/:id
 * body: { response_status, arrived_at?, resolved_at? }
 * Pass whichever timestamp naturally accompanies the new status
 * (e.g. status EN_ROUTE -> no timestamp yet, ON_SCENE -> arrived_at = now,
 * RESOLVED -> resolved_at = now). The page below handles that logic.
 */
export async function updateResponseStatus(id, status, timestampField) {
  const accidentById = Object.fromEntries(mockAccidents.map((a) => [a.accident_id, a]));
  const userById = Object.fromEntries(mockUsers.map((u) => [u.user_id, u]));
  const patch = { response_status: status };
  if (timestampField) patch[timestampField] = new Date().toISOString();

  if (USE_MOCK_DATA) {
    await fakeDelay();
    localResponses = localResponses.map((r) =>
      r.response_id === id ? { ...r, ...patch } : r
    );
    return mapResponse(localResponses.find((r) => r.response_id === id), accidentById, userById);
  }
  const { data } = await axiosClient.patch(`/emergency-responses/${id}`, patch);
  return mapResponse(data, accidentById, userById);
}
