import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import {
  getDashboardStats,
  getDashboardTrend,
  getRoads,
  getAccidentLayer,
  getTrafficLayer,
  getHotspots,
  getAnomalies,
} from '../api_services';

const DONUT_COLORS = ['#3E7CB1', '#E8A33D', '#D14343', '#3FA772', '#8B5CF6', '#7A828C'];

function Donut({ data, height = 180 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-[180px] items-center justify-center text-xs text-slate-400 dark:text-asphalt-500">
        No data yet
      </div>
    );
  }
  const total = data.reduce((sum, d) => sum + d.value, 0);
  return (
    <div className="flex items-center gap-4">
      <div style={{ width: height, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="95%" paddingAngle={2}>
              {data.map((entry, i) => (
                <Cell key={entry.name} fill={DONUT_COLORS[i % DONUT_COLORS.length]} stroke="none" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: '#1D2126', border: '1px solid #282D34', borderRadius: 6, fontSize: 12 }}
              formatter={(value, name) => [`${value} (${((value / total) * 100).toFixed(0)}%)`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex-1 space-y-1.5">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center justify-between gap-2 text-xs">
            <span className="flex items-center gap-1.5 text-slate-600 dark:text-asphalt-300">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }} />
              {d.name}
            </span>
            <span className="font-semibold text-slate-900 dark:text-asphalt-100">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CardShell({ title, action, children }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-asphalt-700 dark:bg-asphalt-900">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-bold text-slate-900 dark:text-asphalt-100">{title}</p>
        {action}
      </div>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [roads, setRoads] = useState([]);
  const [accidentFeatures, setAccidentFeatures] = useState([]);
  const [trafficFeatures, setTrafficFeatures] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  async function loadData() {
    setIsLoading(true);
    try {
      const [statsRes, historyRes, roadsRes, accidentRes, trafficRes, hotspotsRes, anomaliesRes] = await Promise.all([
        getDashboardStats(),
        getDashboardTrend(),
        getRoads(),
        getAccidentLayer(),
        getTrafficLayer(),
        getHotspots(6),
        getAnomalies(5).catch(() => []),
      ]);
      setStats(statsRes);
      setHistory(historyRes);
      setRoads(roadsRes);
      setAccidentFeatures(accidentRes?.features || []);
      setTrafficFeatures(trafficRes?.features || []);
      setHotspots(hotspotsRes || []);
      setAnomalies(anomaliesRes || []);
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

  const severityBreakdown = useMemo(() => {
    const counts = {};
    for (const f of accidentFeatures) {
      const sev = (f.properties?.severity || 'UNKNOWN').toUpperCase();
      counts[sev] = (counts[sev] || 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [accidentFeatures]);

  const congestionBreakdown = useMemo(() => {
    const counts = {};
    for (const f of trafficFeatures) {
      const lvl = (f.properties?.congestion_level || 'UNKNOWN').toUpperCase();
      counts[lvl] = (counts[lvl] || 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [trafficFeatures]);

  const topHotspot = hotspots?.[0];
  const maxHotspotCount = Math.max(1, ...(hotspots || []).map((h) => h.accident_count || 0));

  const insights = useMemo(() => {
    const list = [];
    const highCongestion = congestionBreakdown.find((c) => c.name === 'HIGH' || c.name === 'SEVERE');
    const totalCongestionSamples = congestionBreakdown.reduce((s, c) => s + c.value, 0);
    if (highCongestion && totalCongestionSamples > 0) {
      list.push(`${Math.round((highCongestion.value / totalCongestionSamples) * 100)}% of monitored roads are at HIGH or SEVERE congestion right now.`);
    }
    if (topHotspot) {
      list.push(`${topHotspot.zone_name || 'Top zone'} is the highest accident hotspot with ${topHotspot.accident_count} recorded accidents.`);
    }
    if (anomalies.length > 0) {
      list.push(`${anomalies.length} traffic anomal${anomalies.length === 1 ? 'y has' : 'ies have'} been detected recently — review the Anomalies page.`);
    }
    if (stats?.accidentAlerts) {
      list.push(`${stats.accidentAlerts} severe/fatal accident alert(s) currently require attention.`);
    }
    if (list.length === 0) {
      list.push('No significant risk signals detected — system operating within normal parameters.');
    }
    return list;
  }, [congestionBreakdown, topHotspot, anomalies, stats]);

  if (isLoading) {
    return <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading dashboard…</p>;
  }

  return (
    <div className="space-y-6">
      {/* Header controls & Live API Status */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-asphalt-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold tracking-wider text-emerald-500 dark:text-emerald-400 uppercase">
              Live Backend API Active
            </span>
            {lastUpdated && (
              <span className="text-xs text-slate-400 dark:text-asphalt-500">· Synced at {lastUpdated}</span>
            )}
          </div>
          <p className="mt-1 font-mono text-[11px] font-bold uppercase tracking-widest text-signal-blue">
            Executive Overview
          </p>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">Smart Traffic Dashboard</h1>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-md border border-slate-200 dark:border-asphalt-700 bg-slate-100 dark:bg-asphalt-800 px-3 py-1.5 text-xs font-medium text-slate-800 dark:text-asphalt-200 transition-colors hover:border-signal-blue/50 hover:bg-slate-200 dark:hover:bg-asphalt-700 hover:text-white disabled:opacity-50"
        >
          <span>{isLoading ? 'Syncing...' : '↻ Refresh Data'}</span>
        </button>
      </div>

      {!stats && !isLoading && (
        <div className="flex items-center gap-2.5 rounded-lg border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-xs text-signal-amber">
          <span>⚠️</span>
          <span>No live statistics available from the backend API. Please verify backend connection.</span>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Active Roads" value={stats?.activeRoads ?? '-'} icon="🛣️" />
        <StatCard label="High Traffic" value={stats?.highTraffic ?? '-'} accent="text-signal-amber" icon="🚦" />
        <StatCard label="Accident Alerts" value={stats?.accidentAlerts ?? '-'} accent="text-signal-red" icon="🚨" />
        <StatCard label="High Risk Zones" value={stats?.highRiskZones ?? '-'} accent="text-signal-red" icon="⚠️" />
        <StatCard label="Total Accidents" value={stats?.totalAccidents ?? '-'} accent="text-slate-800 dark:text-asphalt-200" icon="📋" />
        <StatCard
          label="Avg Speed"
          value={stats?.averageSpeed ? `${stats.averageSpeed} km/h` : '-'}
          accent="text-signal-blue"
          icon="⚡"
        />
      </div>

      {/* Hero panel */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-signal-blue via-signal-blue to-[#2c5d87] p-8 text-white shadow-lg dark:border-asphalt-700">
        <div className="absolute -right-10 -top-10 h-56 w-56 rounded-full bg-white/10" />
        <div className="absolute -bottom-16 right-24 h-40 w-40 rounded-full bg-white/5" />
        <div className="relative max-w-xl">
          <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-white/70">Live Intelligence</p>
          <h2 className="mt-1 text-3xl font-extrabold tracking-tight">See it happen in real time</h2>
          <p className="mt-2 text-sm text-white/85">
            Explore live traffic congestion, accident hotspots, and detected anomalies together on one interactive map —
            with turn-by-turn directions between any two points.
          </p>
          <button
            onClick={() => navigate('/live-map')}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-bold text-signal-blue shadow-sm transition-transform hover:scale-[1.02]"
          >
            Open Live Map →
          </button>
        </div>
      </div>

      {/* Chart Grid — row 1 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CardShell
            title="Vehicle Volume — Live Observation Trend"
            action={stats?.totalTrafficRecords ? (
              <span className="text-xs text-slate-500 dark:text-asphalt-400">Total records: {stats.totalTrafficRecords}</span>
            ) : null}
          >
            {history && history.length > 0 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3E7CB1" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#3E7CB1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#282D34" strokeOpacity={0.15} vertical={false} />
                    <XAxis dataKey="hour" stroke="#7A828C" fontSize={12} />
                    <YAxis stroke="#7A828C" fontSize={12} />
                    <Tooltip
                      contentStyle={{ background: '#1D2126', border: '1px solid #282D34', borderRadius: 6, fontSize: 12 }}
                      formatter={(value) => [`${Number(value).toLocaleString()} vehicles`, 'Volume']}
                      labelFormatter={(label) => `Time: ${label}`}
                    />
                    <Area type="monotone" dataKey="vehicles" stroke="#3E7CB1" strokeWidth={2.5} fill="url(#volumeFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-44 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-asphalt-800 bg-slate-50 dark:bg-asphalt-950/40 p-6 text-center">
                <span className="text-2xl mb-1.5">📈</span>
                <p className="text-sm font-medium text-slate-600 dark:text-asphalt-300">No traffic trend data available</p>
                <p className="mt-1 max-w-sm text-xs text-slate-400 dark:text-asphalt-500">
                  No traffic volume observations were found in the database. Charts will automatically populate as sensor data is ingested.
                </p>
              </div>
            )}
          </CardShell>
        </div>

        <CardShell title="Accidents by Severity">
          <Donut data={severityBreakdown} />
        </CardShell>
      </div>

      {/* Chart Grid — row 2 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <CardShell title="Top Accident Hotspots">
          {hotspots.length === 0 ? (
            <p className="text-xs text-slate-400 dark:text-asphalt-500">No hotspots calculated yet.</p>
          ) : (
            <ul className="space-y-2.5">
              {hotspots.map((h) => (
                <li key={h.hotspot_id}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-700 dark:text-asphalt-200">{h.zone_name || 'Unnamed zone'}</span>
                    <span className="font-semibold text-slate-900 dark:text-asphalt-100">{h.accident_count}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-asphalt-800">
                    <div
                      className="h-full rounded-full bg-signal-red"
                      style={{ width: `${Math.max(6, (h.accident_count / maxHotspotCount) * 100)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardShell>

        <CardShell title="Congestion by Level">
          <Donut data={congestionBreakdown} />
        </CardShell>

        <CardShell title="Key Insights" action={<span className="text-lg">💡</span>}>
          <ul className="space-y-3">
            {insights.map((text, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-600 dark:text-asphalt-300">
                <span className="mt-0.5 text-signal-green">●</span>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </CardShell>
      </div>

      <div>
        <p className="mb-3 text-sm font-bold text-slate-900 dark:text-asphalt-100">Road status</p>
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
