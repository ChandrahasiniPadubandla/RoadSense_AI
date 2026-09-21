import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import ActionMenu from '../components/ActionMenu';
import { useAuth } from '../context/AuthContext';
import { ROLES } from '../utils/constants';
import {
  getAllRoads,
  createRoad,
  updateRoad,
  deleteRoad,
} from '../api_services';

const emptyForm = {
  road_name: '',
  road_type: '',
  start_latitude: '',
  start_longitude: '',
  end_latitude: '',
  end_longitude: '',
  road_capacity: '',
  speed_limit: '',
  road_condition: '',
  number_of_lanes: '',
  is_active: true,
};

function toPayload(form) {
  const num = (v) => (v === '' || v === null || v === undefined ? undefined : Number(v));
  return {
    road_name: form.road_name,
    road_type: form.road_type || undefined,
    start_latitude: num(form.start_latitude),
    start_longitude: num(form.start_longitude),
    end_latitude: num(form.end_latitude),
    end_longitude: num(form.end_longitude),
    road_capacity: num(form.road_capacity),
    speed_limit: num(form.speed_limit),
    road_condition: form.road_condition || undefined,
    number_of_lanes: num(form.number_of_lanes),
    is_active: form.is_active,
  };
}

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';
const labelClass = 'mb-1 block text-xs font-medium text-slate-600 dark:text-asphalt-300';

export default function RoadManagement() {
  const { user } = useAuth();
  const canWrite = user?.role === ROLES.SUPER_ADMIN;

  const [roads, setRoads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  async function load(searchTerm = '') {
    setIsLoading(true);
    setLoadError('');
    try {
      const data = await getAllRoads(searchTerm);
      setRoads(data);
    } catch (err) {
      setLoadError('Could not load roads from the backend.');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(search);
  }

  function openCreateModal() {
    setEditingId(null);
    setForm(emptyForm);
    setFormError('');
    setModalOpen(true);
  }

  function openEditModal(road) {
    setEditingId(road.road_id);
    setForm({
      road_name: road.road_name || '',
      road_type: road.road_type || '',
      start_latitude: road.start_latitude ?? '',
      start_longitude: road.start_longitude ?? '',
      end_latitude: road.end_latitude ?? '',
      end_longitude: road.end_longitude ?? '',
      road_capacity: road.road_capacity ?? '',
      speed_limit: road.speed_limit ?? '',
      road_condition: road.road_condition || '',
      number_of_lanes: road.number_of_lanes ?? '',
      is_active: road.is_active,
    });
    setFormError('');
    setModalOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!form.road_name.trim()) {
      setFormError('Road name is required.');
      return;
    }
    setIsSaving(true);
    setFormError('');
    try {
      const payload = toPayload(form);
      if (editingId) {
        await updateRoad(editingId, payload);
      } else {
        await createRoad(payload);
      }
      setModalOpen(false);
      await load(search);
    } catch (err) {
      const detail = err.response?.data?.detail || err.response?.data?.message || err.message;
      setFormError(typeof detail === 'string' ? detail : 'Failed to save road.');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(road) {
    if (!window.confirm(`Delete road "${road.road_name}"? This cannot be undone.`)) return;
    try {
      await deleteRoad(road.road_id);
      await load(search);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete road.');
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <div>
          <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">Road Management</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
            Real road records from the database. {canWrite ? 'You can add, edit, and remove roads.' : 'Read-only for your role.'}
          </p>
        </div>
        {canWrite && (
          <button
            onClick={openCreateModal}
            className="rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-signal-blue/90"
          >
            + Add Road
          </button>
        )}
      </div>

      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search roads by name…"
          className={`${inputClass} max-w-xs`}
        />
        <button
          type="submit"
          className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:border-signal-blue/50 hover:text-signal-blue dark:border-asphalt-600 dark:text-asphalt-300"
        >
          Search
        </button>
      </form>

      {loadError && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          {loadError}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading roads…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'road_name', header: 'Road' },
            { key: 'road_type', header: 'Type', render: (r) => r.road_type || '—' },
            { key: 'number_of_lanes', header: 'Lanes', render: (r) => r.number_of_lanes ?? '—' },
            { key: 'speed_limit', header: 'Speed limit', render: (r) => (r.speed_limit != null ? `${r.speed_limit} km/h` : '—') },
            { key: 'road_condition', header: 'Condition', render: (r) => r.road_condition || '—' },
            {
              key: 'is_active',
              header: 'Status',
              render: (r) => (
                <span className={r.is_active ? 'text-signal-green' : 'text-signal-red'}>
                  {r.is_active ? 'Active' : 'Inactive'}
                </span>
              ),
            },
            ...(canWrite
              ? [
                  {
                    key: 'actions',
                    header: '',
                    render: (r) => (
                      <div className="flex justify-end">
                        <ActionMenu
                          items={[
                            { label: 'Edit', onClick: () => openEditModal(r) },
                            { label: 'Delete', danger: true, onClick: () => handleDelete(r) },
                          ]}
                        />
                      </div>
                    ),
                  },
                ]
              : []),
          ]}
          rows={roads.map((r) => ({ ...r, id: r.road_id }))}
          emptyMessage="No road segments found in the database. Add a road to get started."
        />
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-6 dark:border-asphalt-700 dark:bg-asphalt-900">
            <h3 className="mb-4 text-base font-semibold text-slate-900 dark:text-asphalt-100">
              {editingId ? 'Edit Road' : 'Add Road'}
            </h3>
            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className={labelClass}>Road name *</label>
                <input
                  className={inputClass}
                  value={form.road_name}
                  onChange={(e) => setForm({ ...form, road_name: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Road type</label>
                  <input className={inputClass} value={form.road_type} onChange={(e) => setForm({ ...form, road_type: e.target.value })} placeholder="Highway, Arterial…" />
                </div>
                <div>
                  <label className={labelClass}>Road condition</label>
                  <input className={inputClass} value={form.road_condition} onChange={(e) => setForm({ ...form, road_condition: e.target.value })} placeholder="Good, Poor…" />
                </div>
                <div>
                  <label className={labelClass}>Lanes</label>
                  <input type="number" className={inputClass} value={form.number_of_lanes} onChange={(e) => setForm({ ...form, number_of_lanes: e.target.value })} />
                </div>
                <div>
                  <label className={labelClass}>Speed limit (km/h)</label>
                  <input type="number" className={inputClass} value={form.speed_limit} onChange={(e) => setForm({ ...form, speed_limit: e.target.value })} />
                </div>
                <div>
                  <label className={labelClass}>Road capacity</label>
                  <input type="number" className={inputClass} value={form.road_capacity} onChange={(e) => setForm({ ...form, road_capacity: e.target.value })} />
                </div>
                <div className="flex items-center gap-2 pt-6">
                  <input
                    id="is_active"
                    type="checkbox"
                    checked={!!form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  <label htmlFor="is_active" className="text-sm text-slate-700 dark:text-asphalt-300">Active</label>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Start latitude</label>
                  <input type="number" step="any" className={inputClass} value={form.start_latitude} onChange={(e) => setForm({ ...form, start_latitude: e.target.value })} />
                </div>
                <div>
                  <label className={labelClass}>Start longitude</label>
                  <input type="number" step="any" className={inputClass} value={form.start_longitude} onChange={(e) => setForm({ ...form, start_longitude: e.target.value })} />
                </div>
                <div>
                  <label className={labelClass}>End latitude</label>
                  <input type="number" step="any" className={inputClass} value={form.end_latitude} onChange={(e) => setForm({ ...form, end_latitude: e.target.value })} />
                </div>
                <div>
                  <label className={labelClass}>End longitude</label>
                  <input type="number" step="any" className={inputClass} value={form.end_longitude} onChange={(e) => setForm({ ...form, end_longitude: e.target.value })} />
                </div>
              </div>

              {formError && <p className="text-xs text-signal-red">{formError}</p>}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-600 dark:border-asphalt-600 dark:text-asphalt-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white hover:bg-signal-blue/90 disabled:opacity-50"
                >
                  {isSaving ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
