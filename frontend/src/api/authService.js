import axiosClient, { USE_MOCK_DATA } from './axiosClient';
import { mockUsers, mockRoles } from '../mock/mockData';

/**
 * Contract expected from the real backend:
 *   POST /auth/login  { email, password }
 *   -> 200 { accessToken: string, user: { id, name, email, role } }
 *   -> 401 { message: string }
 *
 * NOTE on `role`: the users table only stores role_id (FK to roles.role_id).
 * The frontend works with the role NAME (e.g. "SUPER_ADMIN") everywhere —
 * in RoleRoute checks, Sidebar nav filtering, etc. — so the login endpoint
 * should join roles and return role_name as `role` in the response, exactly
 * like the mock branch below does. If your backend instead returns role_id
 * as a number, map it to the name here using getRoles() from userService.js
 * before returning.
 */
export async function login(email, password) {
  if (USE_MOCK_DATA) {
    await fakeDelay();
    const match = mockUsers.find(
      (u) => u.email === email && u.password === password
    );
    if (!match) {
      throw new Error('Invalid email or password');
    }
    const roleName = mockRoles.find((r) => r.role_id === match.role_id)?.role_name;
    const user = {
      id: match.user_id,
      name: match.name,
      email: match.email,
      role: roleName,
    };
    return { accessToken: `mock-token-${user.id}`, user };
  }

  const { data } = await axiosClient.post('/auth/login', { email, password });
  return {
    accessToken: data.access_token,
    user: mapUser(data.user),
  };
}

function mapUser(user) {
  return {
    id: user.user_id,
    name: user.name,
    email: user.email,
    phone: user.phone,
    isActive: user.is_active,
    role: user.role?.role_name || user.role_name || user.role_id,
  };
}

export async function logout() {
  if (!USE_MOCK_DATA) {
    // Optional: tell the backend to invalidate the refresh token / session.
    try {
      await axiosClient.post('/auth/logout');
    } catch {
      // Non-fatal — we clear local session regardless.
    }
  }
}

function fakeDelay(ms = 400) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
