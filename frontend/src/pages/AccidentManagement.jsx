import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { SEVERITY_COLOR } from '../utils/constants';
import * as accidentService from '../api/accidentService';
import * as trafficService from '../api/trafficService';

const EMPTY_FORM = {
  roadId: '',
  date: '',
  time: '',
  weather: 'Clear',
  roadCondition: 'Dry',
  vehicleCount: 1,
  severity: 'MINOR',
  fatalities: 0,
  injuries: 0,
  description: '',
};

export default function AccidentManagement() {
  const [accidents, setAccidents] = useState([]);
  const [roads, setRoads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [isSaving, setIsSaving] = useState(false);

  function loadAccidents() {
    return accidentService.getAccidents().then((data) => {
      setAccidents(data);
      setIsLoading(false);
    });
  }

  useEffect(() => {
    loadAccidents();
    trafficService.getRoads().then(setRoads);
  }, []);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setIsSaving(true);
    try {
      // The accidents table stores a GEOGRAPHY(POINT) location, not a road_id
      // + free-text location — so we send the coordinates of the selected
      // road as a stand-in. Swap this for a map-click picker if you want the
      // exact crash site instead of the road's reference point.
      const selectedRoad = roads.find((r) => r.id === form.roadId);
      await accidentService.createAccident({
        ...form,
        lat: selectedRoad?.lat,
        lng: selectedRoad?.lng,
        vehicleCount: Number(form.vehicleCount),
        fatalities: Number(form.fatalities),
        injuries: Number(form.injuries),
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      await loadAccidents();
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading accident records…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-asphalt-400">{accidents.length} recorded accidents</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-md bg-signal-blue px-3 py-1.5 text-xs font-medium text-white hover:opacity-90"
        >
          {showForm ? 'Cancel' : 'Record accident'}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="grid grid-cols-1 gap-3 rounded-lg border border-asphalt-700 bg-asphalt-900 p-5 md:grid-cols-3"
        >
          <Field label="Location">
            <input
              required
              value={form.location}
              onChange={(e) => updateField('location', e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Date">
            <input
              required
              type="date"
              value={form.date}
              onChange={(e) => updateField('date', e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Time">
            <input
              required
              type="time"
              value={form.time}
              onChange={(e) => updateField('time', e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Weather">
            <select
              value={form.weather}
              onChange={(e) => updateField('weather', e.target.value)}
              className="input"
            >
              {['Clear', 'Rain', 'Fog', 'Cloudy', 'Storm'].map((w) => (
                <option key={w}>{w}</option>
              ))}
            </select>
          </Field>
          <Field label="Road condition">
            <select
              value={form.roadCondition}
              onChange={(e) => updateField('roadCondition', e.target.value)}
              className="input"
            >
              {['Dry', 'Wet', 'Icy', 'Under construction'].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Severity">
            <select
              value={form.severity}
              onChange={(e) => updateField('severity', e.target.value)}
              className="input"
            >
              {['MINOR', 'MODERATE', 'SEVERE', 'FATAL'].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </Field>
          <Field label="Vehicles involved">
            <input
              type="number"
              min="1"
              value={form.vehicleCount}
              onChange={(e) => updateField('vehicleCount', e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Injuries">
            <input
              type="number"
              min="0"
              value={form.injuries}
              onChange={(e) => updateField('injuries', e.target.value)}
              className="input"
            />
          </Field>
          <Field label="Fatalities">
            <input
              type="number"
              min="0"
              value={form.fatalities}
              onChange={(e) => updateField('fatalities', e.target.value)}
              className="input"
            />
          </Field>
          <div className="md:col-span-3">
            <Field label="Description">
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
                className="input"
              />
            </Field>
          </div>
          <div className="md:col-span-3">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-md bg-signal-green px-4 py-2 text-sm font-medium text-asphalt-950 hover:opacity-90 disabled:opacity-50"
            >
              {isSaving ? 'Saving…' : 'Save record'}
            </button>
          </div>
        </form>
      )}

      <DataTable
        columns={[
          { key: 'id', header: 'ID' },
          { key: 'location', header: 'Location' },
          { key: 'date', header: 'Date' },
          { key: 'time', header: 'Time' },
          { key: 'injuries', header: 'Injuries' },
          { key: 'fatalities', header: 'Fatalities' },
          {
            key: 'severity',
            header: 'Severity',
            render: (row) => <LevelBadge level={row.severity} colorMap={SEVERITY_COLOR} />,
          },
        ]}
        rows={accidents}
      />
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block text-xs text-asphalt-400">
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}
