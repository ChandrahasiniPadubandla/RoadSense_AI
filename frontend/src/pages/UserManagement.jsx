import React, { useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import ActionMenu from '../components/ActionMenu';
import EditUserModal from '../components/EditUserModal';
import { useAuth } from '../context/AuthContext';
import { ROLE_LABELS } from '../utils/constants';
import {
  getAdminUsers,
  getAdminRoles,
  updateUserRole,
  updateUserProfile,
  updateUserStatus,
  deleteUser,
} from '../api_services';

// Turns a FastAPI error body (string or validation-error list) into text.
function apiErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (d.msg ? d.msg.replace(/^Value error,\s*/i, '') : JSON.stringify(d))).join(', ');
  }
  if (typeof detail === 'string') return detail;
  return fallback;
}

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [busyUser, setBusyUser] = useState(null);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');

  // Edit form (opened from the row's three-dot menu)
  const { user: currentUser } = useAuth();
  const [editingUserId, setEditingUserId] = useState(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState('');

  // `silent` refreshes the list without swapping the table for "Loading…".
  async function load({ silent = false } = {}) {
    if (!silent) setIsLoading(true);
    setLoadError('');
    try {
      const [usersData, rolesData] = await Promise.all([getAdminUsers(), getAdminRoles()]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err) {
      setLoadError('Could not load users. You may not have permission to view this page.');
    } finally {
      if (!silent) setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(''), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  const filtered = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch =
        !search ||
        u.name?.toLowerCase().includes(search.toLowerCase()) ||
        u.username?.toLowerCase().includes(search.toLowerCase()) ||
        u.email?.toLowerCase().includes(search.toLowerCase());
      const matchesRole = roleFilter === 'ALL' || u.role_name === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, search, roleFilter]);

  const editingUser = editingUserId ? users.find((u) => u.user_id === editingUserId) : null;

  function openEdit(user) {
    setActionError('');
    setEditError('');
    setEditingUserId(user.user_id);
  }

  function closeEdit() {
    if (savingEdit) return;
    setEditingUserId(null);
    setEditError('');
  }

  // Saves only what changed. Username goes to PATCH /admin/users/{id}/profile,
  // role access to PATCH /admin/users/{id}/role.
  async function handleEditSave({ username, roleId }) {
    if (!editingUser) return;
    const target = editingUser;
    setSavingEdit(true);
    setEditError('');
    const saved = [];

    try {
      if (username !== undefined) {
        await updateUserProfile(target.user_id, { username });
        saved.push('Username');
      }
      if (roleId !== undefined) {
        await updateUserRole(target.user_id, roleId);
        saved.push('Role');
      }
      await load({ silent: true });
      setEditingUserId(null);
      setNotice(`${target.name} updated.`);
    } catch (err) {
      let message = apiErrorMessage(err, 'Failed to save changes.');
      if (saved.length > 0) {
        // Part of the change went through — refresh so the form shows the truth.
        await load({ silent: true });
        message = `${saved.join(' and ')} saved, but the rest failed: ${message}`;
      }
      setEditError(message);
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleToggleActive(user) {
    setBusyUser(user.user_id);
    setActionError('');
    try {
      await updateUserStatus(user.user_id, !user.is_active);
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
      await deleteUser(user.user_id);
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
        <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">User Management</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Real registered users from the database. Super Admins can edit a user's username and role access (three-dot menu → Edit), activate/deactivate, or delete accounts.
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
      {notice && (
        <div role="status" className="rounded-lg border border-signal-green/30 bg-signal-green/10 px-4 py-3 text-xs text-signal-green">
          {notice}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading users…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'name', header: 'Name' },
            {
              key: 'username',
              header: 'Username',
              render: (u) => <span className="font-mono text-xs">{u.username || '—'}</span>,
            },
            { key: 'email', header: 'Email' },
            {
              key: 'role_name',
              header: 'Role',
              render: (u) => (
                <span className="inline-block rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:border-asphalt-700 dark:bg-asphalt-800 dark:text-asphalt-200">
                  {ROLE_LABELS[u.role_name] || u.role_name || '—'}
                </span>
              ),
            },
            {
              key: 'is_active',
              header: 'Status',
              render: (u) => (
                <span className={u.is_active ? 'text-signal-green' : 'text-signal-red'}>
                  {u.is_active ? 'Active' : 'Inactive'}
                </span>
              ),
            },
            {
              key: 'is_email_verified',
              header: 'Email verified',
              render: (u) => (u.is_email_verified ? 'Yes' : 'No'),
            },
            {
              key: 'actions',
              header: '',
              render: (u) => (
                <div className="flex justify-end">
                  <ActionMenu
                    items={[
                      {
                        label: 'Edit',
                        disabled: busyUser === u.user_id,
                        onClick: () => openEdit(u),
                      },
                      {
                        label: u.is_active ? 'Deactivate' : 'Activate',
                        disabled: busyUser === u.user_id,
                        onClick: () => handleToggleActive(u),
                      },
                      {
                        label: 'Delete',
                        danger: true,
                        disabled: busyUser === u.user_id,
                        onClick: () => handleDelete(u),
                      },
                    ]}
                  />
                </div>
              ),
            },
          ]}
          rows={filtered.map((u) => ({ ...u, id: u.user_id }))}
          emptyMessage="No users match your search, or no users exist in the database yet."
        />
      )}

      {editingUser && (
        <EditUserModal
          key={editingUser.user_id}
          user={editingUser}
          roles={roles}
          isSelf={Boolean(currentUser?.id) && currentUser.id === editingUser.user_id}
          saving={savingEdit}
          error={editError}
          onClose={closeEdit}
          onSave={handleEditSave}
        />
      )}
    </div>
  );
}
