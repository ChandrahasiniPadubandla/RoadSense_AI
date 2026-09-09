import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import { getDashboardStats, getDashboardTrend, getRoads } from '../api_services';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [roads, setRoads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  async function loadData() {
    setIsLoading(true);
    try {
      const [statsRes, historyRes, roadsRes] = await Promise.all([
        getDashboardStats(),
        getDashboardTrend(),
        getRoads(),
      ]);
      setStats(statsRes);
      setHistory(historyRes);
      setRoads(roadsRes);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (isLoading) {
    return <p className="text-sm text-asphalt-400">Loading dashboard…</p>;
  }

  return (
    <div className="space-y-6">
      {/* Header controls & Live API Status */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-asphalt-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold tracking-wider text-emerald-400 uppercase">
              Live Backend API Active
            </span>
            {lastUpdated && (
              <span className="text-xs text-asphalt-500">· Synced at {lastUpdated}</span>
            )}
          </div>
          <p className="mt-1 text-sm text-asphalt-300">
            Real-time traffic metrics and accident indicators from backend analytics engine.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-md border border-asphalt-700 bg-asphalt-800 px-3 py-1.5 text-xs font-medium text-asphalt-200 transition-colors hover:border-signal-blue/50 hover:bg-asphalt-700 hover:text-white disabled:opacity-50"
        >
          <span>{isLoading ? 'Syncing...' : '↻ Refresh Data'}</span>
        </button>
      </div>

      {/* Stats Warning if unavailable */}
      {!stats && !isLoading && (
        <div className="flex items-center gap-2.5 rounded-lg border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-xs text-signal-amber">
          <span>⚠️</span>
          <span>No live statistics available from the backend API. Please verify backend connection.</span>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Active Roads" value={stats?.activeRoads ?? '-'} />
        <StatCard label="High Traffic" value={stats?.highTraffic ?? '-'} accent="text-signal-amber" />
        <StatCard label="Accident Alerts" value={stats?.accidentAlerts ?? '-'} accent="text-signal-red" />
        <StatCard label="High Risk Zones" value={stats?.highRiskZones ?? '-'} accent="text-signal-red" />
        <StatCard label="Total Accidents" value={stats?.totalAccidents ?? '-'} accent="text-asphalt-200" />
        <StatCard
          label="Avg Speed"
          value={stats?.averageSpeed ? `${stats.averageSpeed} km/h` : '-'}
          accent="text-signal-blue"
        />
      </div>

      {/* Vehicle Volume Trend Card */}
      <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-5">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm font-medium text-asphalt-100">
            Vehicle volume — live observation trend
          </p>
          {stats?.totalTrafficRecords ? (
            <span className="text-xs text-asphalt-400">Total records: {stats.totalTrafficRecords}</span>
          ) : null}
        </div>

        {history && history.length > 0 ? (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid stroke="#282D34" vertical={false} />
                <XAxis dataKey="hour" stroke="#7A828C" fontSize={12} />
                <YAxis stroke="#7A828C" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: '#1D2126',
                    border: '1px solid #282D34',
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                  formatter={(value) => [`${Number(value).toLocaleString()} vehicles`, 'Volume']}
                  labelFormatter={(label) => `Time: ${label}`}
                />
                <Line
                  type="monotone"
                  dataKey="vehicles"
                  stroke="#3E7CB1"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-44 flex-col items-center justify-center rounded-lg border border-dashed border-asphalt-800 bg-asphalt-950/40 p-6 text-center">
            <span className="text-2xl mb-1.5">📈</span>
            <p className="text-sm font-medium text-asphalt-300">No traffic trend data available</p>
            <p className="mt-1 max-w-sm text-xs text-asphalt-500">
              No traffic volume observations were found in the database. Charts will automatically populate as sensor data is ingested.
            </p>
          </div>
        )}
      </div>

      <div>
        <p className="mb-3 text-sm font-medium text-asphalt-100">Road status</p>
        <DataTable
          columns={[
            { key: 'name', header: 'Road' },
            { key: 'vehicleCount', header: 'Vehicles' },
            { key: 'avgSpeed', header: 'Avg speed' },
            { key: 'weather', header: 'Weather' },
            {
              key: 'trafficLevel',
              header: 'Level',
              render: (row) => (
                <LevelBadge level={row.trafficLevel} colorMap={TRAFFIC_LEVEL_COLOR} />
              ),
            },
          ]}
          rows={roads}
          emptyMessage="No road segments found in the database. Add roads or connect live traffic sensors to view records."
        />
      </div>
    </div>
  );
}
