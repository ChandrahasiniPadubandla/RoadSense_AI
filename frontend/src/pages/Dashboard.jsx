import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
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

const LEVEL_BAR_COLOR = { LOW: '#3FA772', MEDIUM: '#E8A33D', HIGH: '#D14343', SEVERE: '#8F1D1D', UNKNOWN: '#7A828C' };
const LEVEL_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'SEVERE', 'UNKNOWN'];

const DONUT_COLORS = ['#3E7CB1', '#E8A33D', '#D14343', '#3FA772', '#8B5CF6', '#7A828C'];

/**
 * Tracks whether the app is currently in dark mode by watching the `dark`
 * class on <html> (the standard Tailwind `darkMode: 'class'` toggle target,
 * matching the `dark:` classes already used throughout this file). Recharts
 * components like <Tooltip contentStyle={...}> take plain inline styles,
 * not Tailwind classes, so they can't pick up dark: variants on their own —
 * this hook is what lets chart colors actually follow the theme toggle.
 */
function useIsDarkMode() {
  const [isDark, setIsDark] = useState(
    () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  );

  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains('dark'));
    });
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  return isDark;
}

function Donut({ data, height = 180, isDark }) {
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
              contentStyle={{
                background: isDark ? '#1D2126' : '#ffffff',
                border: `1px solid ${isDark ? '#282D34' : '#E2E8F0'}`,
                borderRadius: 6,
                fontSize: 12,
                color: isDark ? '#E5E7EB' : '#0F172A',
              }}
              itemStyle={{ color: isDark ? '#E5E7EB' : '#0F172A' }}
              labelStyle={{ color: isDark ? '#E5E7EB' : '#0F172A' }}
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

/** Flat section container: one quiet border, no shadow. */
function Panel({ title, subtitle, action, children, className = '' }) {
  return (
    <section
      className={`rounded-lg border border-slate-200 bg-white dark:border-asphalt-700 dark:bg-asphalt-900 ${className}`}
    >
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3 dark:border-asphalt-800">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-asphalt-100">{title}</h3>
            {subtitle && <p className="mt-0.5 text-xs text-slate-500 dark:text-asphalt-400">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

/** Small uppercase label used to title a block inside a panel. */
function BlockLabel({ children }) {
  return (
    <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-asphalt-400">
      {children}
    </p>
  );
}

/**
 * One metric inside the overview strip. `tone` colours only the status dot
 * and (for primary metrics) the value, so colour always carries meaning.
 */
function Metric({ label, value, unit, hint, tone = 'neutral', size = 'md' }) {
  const toneText = {
    neutral: 'text-slate-900 dark:text-asphalt-100',
    info: 'text-signal-blue',
    warn: 'text-signal-amber',
    danger: 'text-signal-red',
  }[tone];
  const dot = {
    neutral: 'bg-slate-300 dark:bg-asphalt-600',
    info: 'bg-signal-blue',
    warn: 'bg-signal-amber',
    danger: 'bg-signal-red',
  }[tone];

  return (
    <div className="min-w-0 px-5 py-4">
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
        <p className="truncate text-xs font-medium text-slate-500 dark:text-asphalt-400">{label}</p>
      </div>
      <p
        className={`data-num mt-1.5 font-bold tracking-tight ${toneText} ${
          size === 'lg' ? 'text-3xl' : 'text-2xl'
        }`}
      >
        {value}
        {unit && <span className="ml-1 text-sm font-medium text-slate-400 dark:text-asphalt-500">{unit}</span>}
      </p>
      {hint && <p className="mt-0.5 truncate text-xs text-slate-400 dark:text-asphalt-500">{hint}</p>}
    </div>
  );
}

function TrendChip({ delta }) {
  if (delta == null || !Number.isFinite(delta)) return null;
  const flat = Math.abs(delta) < 0.5;
  const up = delta > 0;
  const Icon = flat ? Minus : up ? TrendingUp : TrendingDown;
  const tone = flat
    ? 'text-slate-500 bg-slate-100 dark:text-asphalt-300 dark:bg-asphalt-800'
    : up
    ? 'text-signal-amber bg-signal-amber/10'
    : 'text-signal-green bg-signal-green/10';
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium ${tone}`}>
      <Icon size={12} />
      {flat ? 'Stable' : `${up ? '+' : ''}${delta.toFixed(1)}%`}
      <span className="font-normal opacity-70">vs previous</span>
    </span>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const isDark = useIsDarkMode();
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

  // Network status bar: how many monitored road segments sit at each level (from the live road list).
  const networkStatus = useMemo(() => {
    const counts = {};
    for (const r of roads) {
      const lvl = (r.trafficLevel || 'UNKNOWN').toUpperCase();
      counts[lvl] = (counts[lvl] || 0) + 1;
    }
    const total = roads.length;
    return {
      total,
      segments: LEVEL_ORDER.filter((l) => counts[l]).map((l) => ({ level: l, count: counts[l], pct: (counts[l] / total) * 100 })),
    };
  }, [roads]);

  // Real trend indicator: change between the two most recent volume observations.
  const volumeDelta = useMemo(() => {
    if (!history || history.length < 2) return null;
    const last = history[history.length - 1].vehicles;
    const prev = history[history.length - 2].vehicles;
    if (!prev) return null;
    return ((last - prev) / prev) * 100;
  }, [history]);

  const topHotspot = hotspots?.[0];
  const maxHotspotCount = Math.max(1, ...(hotspots || []).map((h) => h.accident_count || 0));

  const insights = useMemo(() => {
    const list = [];
    const highCongestion = congestionBreakdown.find((c) => c.name === 'HIGH' || c.name === 'SEVERE');
    const totalCongestionSamples = congestionBreakdown.reduce((s, c) => s + c.value, 0);
    if (highCongestion && totalCongestionSamples > 0) {
      list.push({
        tone: 'warn',
        text: `${Math.round((highCongestion.value / totalCongestionSamples) * 100)}% of monitored roads are at HIGH or SEVERE congestion right now.`,
      });
    }
    if (topHotspot) {
      list.push({
        tone: 'danger',
        text: `${topHotspot.zone_name || 'Top zone'} is the highest accident hotspot with ${topHotspot.accident_count} recorded accidents.`,
      });
    }
    if (anomalies.length > 0) {
      list.push({
        tone: 'warn',
        text: `${anomalies.length} traffic anomal${anomalies.length === 1 ? 'y has' : 'ies have'} been detected recently — review the Anomalies page.`,
      });
    }
    if (stats?.accidentAlerts) {
      list.push({ tone: 'danger', text: `${stats.accidentAlerts} severe/fatal accident alert(s) currently require attention.` });
    }
    if (list.length === 0) {
      list.push({ tone: 'ok', text: 'No significant risk signals detected — system operating within normal parameters.' });
    }
    return list;
  }, [congestionBreakdown, topHotspot, anomalies, stats]);

  if (isLoading && !stats && roads.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading dashboard…</p>;
  }

  const dash = '–';
  const fmt = (v) => (v == null ? dash : typeof v === 'number' ? v.toLocaleString() : v);
  const insightDot = { ok: 'bg-signal-green', warn: 'bg-signal-amber', danger: 'bg-signal-red' };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-signal-blue">Executive Overview</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">
            Smart Traffic Dashboard
          </h1>
          <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-500 dark:text-asphalt-400">
            <span className="relative flex h-2 w-2">
              <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${stats ? 'animate-ping bg-emerald-400' : 'bg-signal-amber'}`} />
              <span className={`relative inline-flex h-2 w-2 rounded-full ${stats ? 'bg-emerald-500' : 'bg-signal-amber'}`} />
            </span>
            <span className="font-medium">{stats ? 'Live data connected' : 'Backend unavailable'}</span>
            {lastUpdated && <span>· Synced {lastUpdated}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/live-map')}
            className="inline-flex items-center gap-1.5 rounded-md bg-signal-blue px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90"
          >
            Open Live Map <ArrowRight size={14} />
          </button>
          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-signal-blue/50 disabled:opacity-50 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-200"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            {isLoading ? 'Syncing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {!stats && (
        <div className="rounded-lg border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-xs text-signal-amber">
          No live statistics available from the backend API. Please verify backend connection.
        </div>
      )}

      {/* Overview strip: ONE panel, grouped metrics separated by dividers */}
      <Panel>
        <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-5 lg:divide-x lg:divide-y-0">
          <div className="lg:col-span-2">
            <p className="px-5 pt-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-asphalt-400">
              Traffic network
            </p>
            <div className="grid grid-cols-3 divide-x divide-slate-100 dark:divide-asphalt-800">
              <Metric size="lg" label="Active roads" value={fmt(stats?.activeRoads)} hint={stats?.totalRoads ? `of ${stats.totalRoads} registered` : undefined} />
              <Metric size="lg" label="High traffic" value={fmt(stats?.highTraffic)} tone="warn" hint="roads congested" />
              <Metric size="lg" label="Avg speed" value={stats?.averageSpeed ? stats.averageSpeed : dash} unit={stats?.averageSpeed ? 'km/h' : undefined} tone="info" hint="network-wide" />
            </div>
          </div>
          <div className="lg:col-span-3">
            <p className="px-5 pt-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-asphalt-400">
              Safety
            </p>
            <div className="grid grid-cols-2 divide-x divide-slate-100 dark:divide-asphalt-800 sm:grid-cols-4">
              <Metric size="lg" label="Accident alerts" value={fmt(stats?.accidentAlerts)} tone={stats?.accidentAlerts ? 'danger' : 'neutral'} hint="need attention" />
              <Metric size="lg" label="High-risk zones" value={fmt(stats?.highRiskZones)} tone={stats?.highRiskZones ? 'danger' : 'neutral'} />
              <Metric size="lg" label="Accidents today" value={fmt(stats?.accidentsToday)} />
              <Metric size="lg" label="Total accidents" value={fmt(stats?.totalAccidents)} hint="all time" />
            </div>
          </div>
        </div>

        {/* Network status bar */}
        {networkStatus.total > 0 && (
          <div className="border-t border-slate-100 px-5 py-3 dark:border-asphalt-800">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-medium text-slate-600 dark:text-asphalt-300">
                Road network status · {networkStatus.total} segments
              </span>
              <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-500 dark:text-asphalt-400">
                {networkStatus.segments.map((seg) => (
                  <li key={seg.level} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: LEVEL_BAR_COLOR[seg.level] }} />
                    {seg.level.charAt(0) + seg.level.slice(1).toLowerCase()}
                    <span className="data-num font-semibold text-slate-700 dark:text-asphalt-200">{seg.count}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-asphalt-800">
              {networkStatus.segments.map((seg) => (
                <div key={seg.level} title={`${seg.level}: ${seg.count}`} style={{ width: `${seg.pct}%`, backgroundColor: LEVEL_BAR_COLOR[seg.level] }} />
              ))}
            </div>
          </div>
        )}
      </Panel>

      {/* Analytics: volume trend + severity split share one panel */}
      <Panel
        title="Traffic & safety analytics"
        subtitle="Live vehicle volume and accident severity from recorded observations"
        action={stats?.totalTrafficRecords ? <span className="text-xs text-slate-500 dark:text-asphalt-400">{stats.totalTrafficRecords.toLocaleString()} traffic records</span> : null}
      >
        <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          <div className="p-5 lg:col-span-2">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <BlockLabel>Vehicle volume — observation trend</BlockLabel>
              <TrendChip delta={volumeDelta} />
            </div>
            {history && history.length > 0 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3E7CB1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#3E7CB1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={isDark ? '#282D34' : '#E2E8F0'} strokeOpacity={isDark ? 0.4 : 0.8} vertical={false} />
                    <XAxis dataKey="hour" stroke={isDark ? '#7A828C' : '#64748B'} fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke={isDark ? '#7A828C' : '#64748B'} fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: isDark ? '#1D2126' : '#ffffff',
                        border: `1px solid ${isDark ? '#282D34' : '#E2E8F0'}`,
                        borderRadius: 6,
                        fontSize: 12,
                        color: isDark ? '#E5E7EB' : '#0F172A',
                      }}
                      itemStyle={{ color: isDark ? '#E5E7EB' : '#0F172A' }}
                      labelStyle={{ color: isDark ? '#94A3B8' : '#64748B' }}
                      formatter={(value) => [`${Number(value).toLocaleString()} vehicles`, 'Volume']}
                      labelFormatter={(label) => `Time: ${label}`}
                    />
                    <Area type="monotone" dataKey="vehicles" stroke="#3E7CB1" strokeWidth={2} fill="url(#volumeFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex h-44 flex-col items-center justify-center rounded-md bg-slate-50 p-6 text-center dark:bg-asphalt-950/40">
                <p className="text-sm font-medium text-slate-600 dark:text-asphalt-300">No traffic trend data available</p>
                <p className="mt-1 max-w-sm text-xs text-slate-400 dark:text-asphalt-500">
                  No traffic volume observations were found in the database. The chart populates automatically as sensor data is ingested.
                </p>
              </div>
            )}
          </div>

          <div className="p-5">
            <BlockLabel>Accidents by severity</BlockLabel>
            <Donut data={severityBreakdown} isDark={isDark} height={150} />
          </div>
        </div>
      </Panel>

      {/* Risk: hotspots, congestion split and insights share one panel */}
      <Panel title="Risk & congestion" subtitle="Where problems concentrate and what needs attention">
        <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          <div className="p-5">
            <BlockLabel>Top accident hotspots</BlockLabel>
            {hotspots.length === 0 ? (
              <p className="text-xs text-slate-400 dark:text-asphalt-500">No hotspots calculated yet.</p>
            ) : (
              <ul className="space-y-3">
                {hotspots.map((h) => (
                  <li key={h.hotspot_id}>
                    <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                      <span className="truncate font-medium text-slate-700 dark:text-asphalt-200">{h.zone_name || 'Unnamed zone'}</span>
                      <span className="data-num font-semibold text-slate-900 dark:text-asphalt-100">{h.accident_count}</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-asphalt-800">
                      <div className="h-full rounded-full bg-signal-red" style={{ width: `${Math.max(6, (h.accident_count / maxHotspotCount) * 100)}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="p-5">
            <BlockLabel>Congestion by level</BlockLabel>
            <Donut data={congestionBreakdown} isDark={isDark} height={150} />
          </div>

          <div className="p-5">
            <BlockLabel>Key insights</BlockLabel>
            <ul className="space-y-3">
              {insights.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs leading-relaxed text-slate-600 dark:text-asphalt-300">
                  <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${insightDot[item.tone]}`} />
                  <span>{item.text}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Panel>

      {/* Road status (paginated) */}
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-asphalt-100">Road status</h3>
          <span className="text-xs text-slate-500 dark:text-asphalt-400">Latest reading per monitored road</span>
        </div>
        <DataTable
          label="roads"
          columns={[
            { key: 'name', header: 'Road' },
            { key: 'vehicleCount', header: 'Vehicles' },
            { key: 'avgSpeed', header: 'Avg speed' },
            { key: 'weather', header: 'Weather' },
            {
              key: 'trafficLevel',
              header: 'Level',
              render: (row) => <LevelBadge level={row.trafficLevel} colorMap={TRAFFIC_LEVEL_COLOR} />,
            },
          ]}
          rows={roads}
          emptyMessage="No road segments found in the database. Add roads or connect live traffic sensors to view records."
        />
      </section>
    </div>
  );
}
