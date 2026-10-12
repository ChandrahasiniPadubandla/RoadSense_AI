import React, { useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import { ROLE_LABELS } from '../utils/constants';
import {
  getAdminUsers,
  getAdminRoles,
  updateUserRole,
  updateUserStatus,
  deleteUser,
} from '../api_services';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [busyUser, setBusyUser] = useState(null);
  const [actionError, setActionError] = useState('');

  async function load() {
    setIsLoading(true);
    setLoadError('');
    try {
      const [usersData, rolesData] = await Promise.all([getAdminUsers(), getAdminRoles()]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err) {
      setLoadError('Could not load users. You may not have permission to view this page.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch =
        !search ||
        u.name?.toLowerCase().includes(search.toLowerCase()) ||
        u.email?.toLowerCase().includes(search.toLowerCase());
      const matchesRole = roleFilter === 'ALL' || u.role_name === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, search, roleFilter]);

  async function handleRoleChange(user, roleId) {
    setBusyUser(user.user_id);
    setActionError('');
    try {
      await updateUserRole(user.name, roleId);
      await load();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to update role.');
    } finally {
      setBusyUser(null);
    }
  }

  async function handleToggleActive(user) {
    setBusyUser(user.user_id);
    setActionError('');
    try {
      await updateUserStatus(user.name, !user.is_active);
      await load();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to update status.');
    } finally {
      setBusyUser(null);
    }
  }

  async function handleDelete(user) {
    if (!window.confirm(`Permanently delete user "${user.name}" (${user.email})?`)) return;
    setBusyUser(user.user_id);
    setActionError('');
    try {
      await deleteUser(user.name);
      await load();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to delete user.');
    } finally {
      setBusyUser(null);
    }
  }

  const inputClass =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-asphalt-100">User Management</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Real registered users from the database. Super Admins can change roles, activate/deactivate, or delete accounts.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or email…"
          className={`${inputClass} max-w-xs`}
        />
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className={inputClass}>
          <option value="ALL">All roles</option>
          {Object.keys(ROLE_LABELS).map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </select>
      </div>

      {loadError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {loadError}
        </div>
      )}
      {actionError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {actionError}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading users…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'name', header: 'Name' },
            { key: 'email', header: 'Email' },
            {
              key: 'role_name',
              header: 'Role',
              render: (u) => (
                <select
                  value={u.role_id || ''}
                  disabled={busyUser === u.user_id || roles.length === 0}
                  onChange={(e) => handleRoleChange(u, e.target.value)}
                  className={`${inputClass} py-1 text-xs`}
                >
                  {roles.map((r) => (
                    <option key={r.role_id} value={r.role_id}>
                      {ROLE_LABELS[r.role_name] || r.role_name}
                    </option>
                  ))}
                </select>
              ),
            },
            {
              key: 'is_active',
              header: 'Status',
              render: (u) => (
                <button
                  onClick={() => handleToggleActive(u)}
                  disabled={busyUser === u.user_id}
                  className={u.is_active ? 'text-signal-green hover:underline' : 'text-signal-red hover:underline'}
                >
                  {u.is_active ? 'Active' : 'Inactive'}
                </button>
              ),
            },
            {
              key: 'is_email_verified',
              header: 'Email verified',
              render: (u) => (u.is_email_verified ? 'Yes' : 'No'),
            },
            {
              key: 'actions',
              header: 'Actions',
              render: (u) => (
                <button
                  onClick={() => handleDelete(u)}
                  disabled={busyUser === u.user_id}
                  className="text-signal-red hover:underline"
                >
                  Delete
                </button>
              ),
            },
          ]}
          rows={filtered.map((u) => ({ ...u, id: u.user_id }))}
          emptyMessage="No users match your search, or no users exist in the database yet."
        />
      )}
    </div>
  );
}
