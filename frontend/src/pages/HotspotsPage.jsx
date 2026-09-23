import React, { useEffect, useState, useMemo } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { RISK_LEVEL_COLOR } from '../utils/constants';
import { getHotspots } from '../api_services';

export default function HotspotsPage() {
  const [hotspots, setHotspots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('ALL');

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      const data = await getHotspots(20);
      setHotspots(data);
      setIsLoading(false);
    })();
  }, []);

  const levels = useMemo(() => {
    const set = new Set(hotspots.map((h) => (h.risk_level || 'LOW').toUpperCase()));
    return Array.from(set);
  }, [hotspots]);

  const filteredHotspots = useMemo(() => {
    if (activeFilter === 'ALL') return hotspots;
    return hotspots.filter((h) => (h.risk_level || 'LOW').toUpperCase() === activeFilter);
  }, [hotspots, activeFilter]);

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">Accident Hotspots</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Zones ranked by recorded accident count, calculated from the real{' '}
          <code className="rounded bg-slate-100 px-1 py-0.5 text-xs dark:bg-asphalt-800">accident_hotspots</code> database table —
          the same data source the chatbot uses.
        </p>
      </div>

      {!isLoading && (
        <div className="flex items-center gap-2">
          <label htmlFor="risk-filter" className="text-sm font-medium text-slate-600 dark:text-asphalt-300">
            Filter by risk level:
          </label>
          <select
            id="risk-filter"
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-200"
          >
            <option value="ALL">All</option>
            {levels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading hotspots…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'zone_name', header: 'Zone', render: (h) => h.zone_name || 'Unnamed zone' },
            { key: 'accident_count', header: 'Accidents', render: (h) => h.accident_count ?? 0 },
            {
              key: 'risk_level',
              header: 'Risk level',
              render: (h) => <LevelBadge level={(h.risk_level || 'LOW').toUpperCase()} colorMap={RISK_LEVEL_COLOR} />,
            },
            { key: 'risk_score', header: 'Risk score', render: (h) => (h.risk_score != null ? h.risk_score : '—') },
            {
              key: 'coords',
              header: 'Coordinates',
              render: (h) => (h.latitude != null && h.longitude != null ? `${h.latitude.toFixed(4)}, ${h.longitude.toFixed(4)}` : '—'),
            },
            {
              key: 'calculated_at',
              header: 'Last calculated',
              render: (h) => (h.calculated_at ? new Date(h.calculated_at).toLocaleString() : '—'),
            },
          ]}
          rows={filteredHotspots.map((h) => ({ ...h, id: h.hotspot_id }))}
          emptyMessage={
            activeFilter === 'ALL'
              ? 'No accident hotspots have been calculated yet. Run the hotspot detection pipeline to populate this table.'
              : `No ${activeFilter.toLowerCase()} risk hotspots found.`
          }
        />
      )}
    </div>
  );
}