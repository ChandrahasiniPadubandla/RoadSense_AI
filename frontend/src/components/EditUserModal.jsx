import React, { useEffect, useRef, useState } from 'react';
import { ROLE_LABELS } from '../utils/constants';

/**
 * Modal form for editing a user's username and role access (Super Admin).
 *
 * Nothing is sent to the server until "Save changes" is pressed; the parent
 * receives only the fields that actually changed:
 *   onSave({ username?: string, roleId?: string })
 *
 * Username rules mirror the backend (UserProfileUpdate in schemas/auth.py):
 * 3-50 characters, letters / numbers / _ . - only; stored in lowercase.
 */

const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]+$/;

function validateUsername(value) {
  if (!value) return 'Username is required.';
  if (value.length < 3) return 'Username must be at least 3 characters.';
  if (value.length > 50) return 'Username must be 50 characters or fewer.';
  if (!USERNAME_PATTERN.test(value)) {
    return 'Use only letters, numbers, dots, dashes and underscores (no spaces).';
  }
  return '';
}

export default function EditUserModal({
  user,
  roles,
  isSelf = false,
  saving = false,
  error = '',
  onClose,
  onSave,
}) {
  const [username, setUsername] = useState(user.username || '');
  const [roleId, setRoleId] = useState(user.role_id || '');
  const [submitted, setSubmitted] = useState(false);
  const usernameRef = useRef(null);

  // Focus the first field when the dialog opens.
  useEffect(() => {
    usernameRef.current?.focus();
    usernameRef.current?.select();
  }, []);

  // Esc closes the dialog (unless a save is in flight).
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape' && !saving) onClose();
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [saving, onClose]);

  const normalizedUsername = username.trim().toLowerCase();
  const usernameChanged = normalizedUsername !== (user.username || '').toLowerCase();
  const roleChanged = Boolean(roleId) && roleId !== user.role_id;
  const usernameError = usernameChanged ? validateUsername(normalizedUsername) : '';
  const hasChanges = usernameChanged || roleChanged;
  const canSave = hasChanges && !usernameError && !saving;

  const selectedRole = roles.find((r) => r.role_id === roleId);
  const losesAdminAccess =
    isSelf && roleChanged && selectedRole && selectedRole.role_name !== 'SUPER_ADMIN';

  function handleSubmit(e) {
    e.preventDefault();
    setSubmitted(true);
    if (!canSave) return;
    onSave({
      username: usernameChanged ? normalizedUsername : undefined,
      roleId: roleChanged ? roleId : undefined,
    });
  }

  const inputClass =
    'mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue disabled:opacity-60 dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';
  const labelClass = 'block text-xs font-medium text-slate-600 dark:text-asphalt-300';

  return (
    <div
      className="fixed inset-0 z-[1200] flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
    >
      <form
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-user-title"
        noValidate
        className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 id="edit-user-title" className="text-lg font-bold text-slate-900 dark:text-asphalt-100">
              Edit user
            </h3>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-asphalt-400">
              Change the username or role access, then save.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 disabled:opacity-50 dark:text-asphalt-400 dark:hover:bg-asphalt-800"
          >
            ✕
          </button>
        </div>

        {/* Read-only context so it's clear who is being edited */}
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs dark:border-asphalt-700 dark:bg-asphalt-800/60">
          <p className="font-medium text-slate-800 dark:text-asphalt-100">{user.name}</p>
          <p className="text-slate-500 dark:text-asphalt-400">{user.email}</p>
        </div>

        <label className={`${labelClass} mt-4`} htmlFor="edit-username">
          Username
        </label>
        <input
          ref={usernameRef}
          id="edit-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={saving}
          autoComplete="off"
          spellCheck={false}
          maxLength={60}
          aria-invalid={Boolean(usernameError)}
          className={inputClass}
        />
        {usernameError && (submitted || username.trim().length > 0) ? (
          <p className="mt-1 text-[11px] text-signal-red">{usernameError}</p>
        ) : (
          <p className="mt-1 text-[11px] text-slate-400 dark:text-asphalt-500">
            3–50 characters. Letters, numbers, . - _ only. Saved in lowercase.
          </p>
        )}

        <label className={`${labelClass} mt-4`} htmlFor="edit-role">
          Role access
        </label>
        <select
          id="edit-role"
          value={roleId}
          onChange={(e) => setRoleId(e.target.value)}
          disabled={saving || roles.length === 0}
          className={inputClass}
        >
          {roles.map((r) => (
            <option key={r.role_id} value={r.role_id}>
              {ROLE_LABELS[r.role_name] || r.role_name}
            </option>
          ))}
        </select>
        {selectedRole?.description && (
          <p className="mt-1 text-[11px] text-slate-400 dark:text-asphalt-500">{selectedRole.description}</p>
        )}

        {losesAdminAccess && (
          <p className="mt-3 rounded-md border border-signal-amber/40 bg-signal-amber/10 px-3 py-2 text-[11px] text-signal-amber">
            This is your own account. After saving you will lose Super Admin access, including this page.
          </p>
        )}

        {error && (
          <p role="alert" className="mt-3 rounded-md border border-signal-red/40 bg-signal-red/10 px-3 py-2 text-xs text-signal-red">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 disabled:opacity-50 dark:border-asphalt-600 dark:text-asphalt-200 dark:hover:bg-asphalt-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSave}
            className="rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </form>
    </div>
  );
}
