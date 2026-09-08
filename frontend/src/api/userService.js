import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { mockUsers, mockRoles } from '../mock/mockData';

function fakeDelay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mapUser(row, roleNameById) {
  return {
    id: row.user_id,
    name: row.name,
    email: row.email,
    phone: row.phone,
    isActive: row.is_active,
    role: roleNameById[row.role_id] || row.role_id,
  };
}

/** GET /users (joined with roles for role_name) */
export async function getUsers() {
  const roleNameById = Object.fromEntries(mockRoles.map((r) => [r.role_id, r.role_name]));
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockUsers.map((u) => mapUser(u, roleNameById));
  }
  const { data } = await axiosClient.get('/users');
  return data.map((u) => mapUser(u, roleNameById));
}

/** GET /roles */
export async function getRoles() {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    return mockRoles.map((r) => ({ id: r.role_id, name: r.role_name, description: r.description }));
  }
  const { data } = await axiosClient.get('/roles');
  return data.map((r) => ({ id: r.role_id, name: r.role_name, description: r.description }));
}
