import React, { useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import { getTrafficRecords, getAllRoads } from '../api_services';

const LEVEL_OPTIONS = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'SEVERE'];

export default function TrafficManagement() {
  const [records, setRecords] = useState([]);
  const [roadsById, setRoadsById] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('ALL');

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      const [trafficData, roadsData] = await Promise.all([getTrafficRecords(), getAllRoads()]);
      setRecords(trafficData);
      setRoadsById(Object.fromEntries(roadsData.map((r) => [r.road_id, r.road_name])));
      setIsLoading(false);
    })();
  }, []);

  const filtered = useMemo(() => {
    return records.filter((r) => {
      const roadName = roadsById[r.road_id] || '';
      const matchesSearch = !search || roadName.toLowerCase().includes(search.toLowerCase());
      const matchesLevel = levelFilter === 'ALL' || (r.congestion_level || '').toUpperCase() === levelFilter;
      return matchesSearch && matchesLevel;
    });
  }, [records, roadsById, search, levelFilter]);

  const inputClass =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-4 dark:border-asphalt-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-asphalt-100">Traffic Management</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
          Real recorded traffic observations from the database — vehicle counts, speeds, congestion levels, and conditions.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by road name…"
          className={`${inputClass} max-w-xs`}
        />
        <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)} className={inputClass}>
          {LEVEL_OPTIONS.map((lvl) => (
            <option key={lvl} value={lvl}>
              {lvl === 'ALL' ? 'All congestion levels' : lvl}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading traffic records…</p>
      ) : (
        <DataTable
          columns={[
            { key: 'road', header: 'Road', render: (r) => roadsById[r.road_id] || r.road_id },
            {
              key: 'timestamp',
              header: 'Recorded',
              render: (r) => (r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'),
            },
            { key: 'vehicle_count', header: 'Vehicles' },
            { key: 'average_speed', header: 'Avg speed', render: (r) => (r.average_speed != null ? `${r.average_speed} km/h` : '—') },
            {
              key: 'congestion_level',
              header: 'Congestion',
              render: (r) => <LevelBadge level={(r.congestion_level || 'LOW').toUpperCase()} colorMap={TRAFFIC_LEVEL_COLOR} />,
            },
            { key: 'weather_condition', header: 'Weather', render: (r) => r.weather_condition || '—' },
          ]}
          rows={filtered.map((r) => ({ ...r, id: r.traffic_id }))}
          emptyMessage="No traffic records found in the database for this filter."
        />
      )}
    </div>
  );
}
