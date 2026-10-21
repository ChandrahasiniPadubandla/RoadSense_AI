import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw, ArrowRight, TrendingUp, TrendingDown, Minus,
  Route, Flame, Gauge, Siren, ShieldAlert, CalendarClock, Skull, Database,
} from 'lucide-react';
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from 'framer-motion';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import {
  getDashboardStats, getDashboardTrend, getRoads, roadsFromTrafficLayer, getAccidentLayer, getTrafficLayer, getHotspots, getAnomalies,
} from '../api_services';

const LEVEL_BAR_COLOR = { LOW: '#3FA772', MEDIUM: '#E8A33D', HIGH: '#D14343', SEVERE: '#8F1D1D' };
const LEVEL_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'SEVERE'];
const DONUT_COLORS = ['#3E7CB1', '#E8A33D', '#D14343', '#3FA772', '#8B5CF6', '#7A828C'];
const TOWER_SPOTS = [[143, 110], [46, 60], [240, 60], [46, 200], [240, 200], [143, 250]];
const TOWER_COLORS = ['#D14343', '#E8A33D', '#3E7CB1', '#3E7CB1', '#3E7CB1', '#3E7CB1'];

const TABS = [
  { id: 'analytics', label: 'Traffic and safety analysis' },
  { id: 'risk', label: 'Risk and congestion' },
  { id: 'roads', label: 'Road status' },
];

const glass =
  'rounded-xl border border-slate-200/80 bg-white/80 backdrop-blur-md shadow-[0_18px_40px_-24px_rgba(15,23,42,0.35)] ' +
  'dark:border-asphalt-700/70 dark:bg-asphalt-900/60 dark:shadow-[0_18px_40px_-20px_rgba(0,0,0,0.7)]';

function useIsDarkMode() {
  const [isDark, setIsDark] = useState(
    () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  );
  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => setIsDark(root.classList.contains('dark')));
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  return isDark;
}

/** Card that tilts toward the pointer and lifts its content off the surface. */
function Tilt({ children, className = '', max = 9, index = 0 }) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 220, damping: 22 });
  const sy = useSpring(y, { stiffness: 220, damping: 22 });
  const rotateX = useTransform(sy, [-0.5, 0.5], [max, -max]);
  const rotateY = useTransform(sx, [-0.5, 0.5], [-max, max]);
  const sheen = useTransform(
    [sx, sy],
    ([a, b]) => `radial-gradient(circle at ${(a + 0.5) * 100}% ${(b + 0.5) * 100}%, rgba(110,180,240,0.22), transparent 60%)`
  );
  const move = (e) => {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - r.left) / r.width - 0.5);
    y.set((e.clientY - r.top) / r.height - 0.5);
  };
  const leave = () => { x.set(0); y.set(0); };

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 28, rotateX: -22 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ delay: index * 0.06, type: 'spring', stiffness: 120, damping: 16 }}
      style={{ perspective: 900 }}
      className={className}
      onMouseMove={move}
      onMouseLeave={leave}
    >
      <motion.div style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }} className={`relative h-full ${glass}`}>
        <motion.div style={{ background: sheen }} className="pointer-events-none absolute inset-0 rounded-xl" />
        {children}
      </motion.div>
    </motion.div>
  );
}

const TONES = {
  neutral: { text: 'text-slate-900 dark:text-asphalt-100', chip: 'bg-slate-100 text-slate-500 dark:bg-asphalt-800 dark:text-asphalt-300', glow: '' },
  info: { text: 'text-signal-blue', chip: 'bg-signal-blue/15 text-signal-blue', glow: 'shadow-[0_0_24px_-6px_#3E7CB1]' },
  warn: { text: 'text-signal-amber', chip: 'bg-signal-amber/15 text-signal-amber', glow: 'shadow-[0_0_24px_-6px_#E8A33D]' },
  danger: { text: 'text-signal-red', chip: 'bg-signal-red/15 text-signal-red', glow: 'shadow-[0_0_24px_-6px_#D14343]' },
};

function Kpi({ icon: Icon, label, value, unit, hint, tone = 'neutral', index }) {
  const t = TONES[tone];
  return (
    <Tilt index={index}>
      <div className="p-4" style={{ transform: 'translateZ(34px)' }}>
        <div className="flex items-center justify-between">
          <p className="truncate text-xs font-medium text-slate-500 dark:text-asphalt-400">{label}</p>
          <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${t.chip} ${t.glow}`}>
            <Icon size={16} />
          </span>
        </div>
        <p className={`data-num mt-3 text-3xl font-bold tracking-tight ${t.text}`}>
          {value}
          {unit && <span className="ml-1 text-sm font-medium text-slate-400 dark:text-asphalt-500">{unit}</span>}
        </p>
        {hint && <p className="mt-1 truncate text-xs text-slate-400 dark:text-asphalt-500">{hint}</p>}
      </div>
    </Tilt>
  );
}

/** One 3D block: footprint sits on the floor plane, sides rise along +Z. */
function Tower({ x, y, h, color, hotspot, onHover, w = 54 }) {
  const side = (style, dir) => ({
    position: 'absolute',
    background: `linear-gradient(${dir}, ${color}2e, ${color}d9)`,
    border: `1px solid ${color}`,
    ...style,
  });
  return (
    <div
      style={{ position: 'absolute', left: x, top: y, width: w, height: w, transformStyle: 'preserve-3d', cursor: 'pointer' }}
      onPointerMove={(e) => onHover?.({ x: e.clientX, y: e.clientY, hotspot })}
      onPointerLeave={() => onHover?.(null)}
    >
      <div style={{ position: 'absolute', inset: -10, background: `${color}40`, filter: 'blur(12px)' }} />
      <div style={side({ left: 0, top: w, width: w, height: h, transformOrigin: 'top', transform: 'rotateX(90deg)' }, 'to bottom')} />
      <div style={side({ left: 0, top: 0, width: w, height: h, transformOrigin: 'top', transform: 'rotateX(90deg)', opacity: 0.6 }, 'to bottom')} />
      <div style={side({ left: 0, top: 0, width: h, height: w, transformOrigin: 'left', transform: 'rotateY(-90deg)', opacity: 0.75 }, 'to right')} />
      <div style={side({ left: w, top: 0, width: h, height: w, transformOrigin: 'left', transform: 'rotateY(-90deg)' }, 'to right')} />
      <div style={{ position: 'absolute', inset: 0, background: color, border: '1px solid #fff5', boxShadow: `0 0 22px ${color}`, transform: `translateZ(${h}px)` }} />
    </div>
  );
}

/** Drag-to-rotate 3D city of accident hotspots: taller tower = more accidents. */
const HotspotScene = React.memo(function HotspotScene({ hotspots, isDark }) {
  const [tooltip, setTooltip] = useState(null);
  const reduce = useReducedMotion();
  const rz = useMotionValue(-35);
  const dragX = useRef(null);
  useEffect(() => {
    if (reduce) return undefined;
    let raf;
    let last = performance.now();
    const tick = (t) => {
      if (dragX.current == null) rz.set(rz.get() + (t - last) * 0.003);
      last = t;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduce, rz]);

  const max = Math.max(1, ...hotspots.map((h) => h.accident_count || 0));
  const items = hotspots.slice(0, TOWER_SPOTS.length);

  return (
    <div className="relative h-full min-h-[380px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_18px_40px_-24px_rgba(15,23,42,0.25)] dark:border-asphalt-700 dark:bg-[radial-gradient(ellipse_at_50%_35%,#1b2a3b_0%,#0E1013_70%)] dark:shadow-[0_24px_60px_-20px_rgba(62,124,177,0.45)]">
      <div
        className="absolute inset-0 cursor-grab touch-pan-y active:cursor-grabbing"
        style={{ perspective: 1100 }}
        onPointerDown={(e) => { dragX.current = e.clientX; e.currentTarget.setPointerCapture(e.pointerId); }}
        onPointerMove={(e) => { if (dragX.current != null) { rz.set(rz.get() + (e.clientX - dragX.current) * 0.4); dragX.current = e.clientX; } }}
        onPointerUp={() => { dragX.current = null; }}
        onPointerCancel={() => { dragX.current = null; }}
      >
        <motion.div
          style={{ rotateX: 58, rotateZ: rz, scale: 0.7, y: 25, transformStyle: 'preserve-3d', width: 340, height: 340, marginLeft: -170, marginTop: -170 }}
          className="absolute left-1/2 top-1/2"
        >
          <div
            style={{
              position: 'absolute', inset: 0, borderRadius: 8,
              background: isDark ? 'rgba(62,124,177,0.08)' : 'rgba(62,124,177,0.05)',
              border: isDark ? '1px solid rgba(110,180,240,0.5)' : '1px solid rgba(62,124,177,0.35)',
              backgroundImage: isDark
                ? 'linear-gradient(rgba(110,180,240,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(110,180,240,0.3) 1px, transparent 1px)'
                : 'linear-gradient(rgba(62,124,177,0.22) 1px, transparent 1px), linear-gradient(90deg, rgba(62,124,177,0.22) 1px, transparent 1px)',
              backgroundSize: '34px 34px',
              boxShadow: isDark ? '0 0 60px rgba(62,124,177,0.35)' : '0 10px 30px rgba(15,23,42,0.08)',
            }}
          />
          {items.map((h, i) => (
            <Tower key={h.hotspot_id ?? i} x={TOWER_SPOTS[i][0]} y={TOWER_SPOTS[i][1]} color={TOWER_COLORS[i]} h={28 + ((h.accident_count || 0) / max) * 130} hotspot={h} onHover={setTooltip} />
          ))}
        </motion.div>
      </div>

      {tooltip && (
        <div className="pointer-events-none fixed z-[9999]" style={{ left: tooltip.x + 15, top: tooltip.y - 15 }}>
          <div className="min-w-[220px] rounded-xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-asphalt-700 dark:bg-asphalt-900">
            <div className="text-sm font-semibold text-slate-900 dark:text-white">📍 {tooltip.hotspot?.zone_name || 'Unknown Zone'}</div>
            <div className="mt-3 text-xs uppercase tracking-wide text-slate-400">Accident Count</div>
            <div className="text-2xl font-bold text-signal-red">{tooltip.hotspot?.accident_count || 0}</div>
          </div>
        </div>
      )}

      {items.length === 0 && (
        <p className="absolute inset-0 flex items-center justify-center text-sm text-slate-400 dark:text-asphalt-400">No hotspots calculated yet.</p>
      )}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-center gap-x-4 gap-y-1 bg-gradient-to-t from-white via-white/90 to-transparent px-4 pb-3 pt-8 text-xs text-slate-600 dark:from-asphalt-950 dark:via-asphalt-950/90 dark:text-asphalt-300">
        {items.map((h, i) => (
          <span key={h.hotspot_id ?? i} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ background: TOWER_COLORS[i], boxShadow: `0 0 8px ${TOWER_COLORS[i]}` }} />
            {h.zone_name || 'Unnamed zone'}
            <span className="data-num font-semibold text-slate-900 dark:text-asphalt-100">{h.accident_count}</span>
          </span>
        ))}
        <span className="ml-auto text-slate-400 dark:text-asphalt-500">Drag to rotate · taller = more accidents</span>
      </div>
    </div>
  );
});

function Donut({ data, height = 150, isDark }) {
  if (!data || data.length === 0) {
    return <div className="flex h-[150px] items-center justify-center text-xs text-slate-400 dark:text-asphalt-500">No data yet</div>;
  }
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="flex items-center gap-4">
      <div style={{ width: height, height, transform: 'perspective(520px) rotateX(24deg)', filter: 'drop-shadow(0 16px 10px rgba(0,0,0,0.35))' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="60%" outerRadius="96%" paddingAngle={3}>
              {data.map((d, i) => <Cell key={d.name} fill={DONUT_COLORS[i % DONUT_COLORS.length]} stroke="none" />)}
            </Pie>
            <Tooltip
              contentStyle={{ background: isDark ? '#1D2126' : '#fff', border: `1px solid ${isDark ? '#282D34' : '#E2E8F0'}`, borderRadius: 8, fontSize: 12 }}
              itemStyle={{ color: isDark ? '#E5E7EB' : '#0F172A' }}
              formatter={(v, n) => [`${v} (${((v / total) * 100).toFixed(0)}%)`, n]}
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

function Panel({ title, subtitle, children, className = '' }) {
  return (
    <section className={`${glass} ${className}`}>
      {title && (
        <header className="border-b border-slate-100 px-5 py-3 dark:border-asphalt-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-asphalt-100">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-slate-500 dark:text-asphalt-400">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

const BlockLabel = ({ children }) => (
  <p className="mb-3 text-xs font-semibold text-slate-500 dark:text-asphalt-400">{children}</p>
);

function TrendChip({ delta }) {
  if (delta == null || !Number.isFinite(delta)) return null;
  const flat = Math.abs(delta) < 0.5;
  const up = delta > 0;
  const Icon = flat ? Minus : up ? TrendingUp : TrendingDown;
  const tone = flat ? 'text-slate-500 bg-slate-100 dark:text-asphalt-300 dark:bg-asphalt-800' : up ? 'text-signal-amber bg-signal-amber/10' : 'text-signal-green bg-signal-green/10';
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
  const [activeTab, setActiveTab] = useState('analytics');

  async function loadData() {
    setIsLoading(true);
    getDashboardStats().then(setStats).catch((err) => console.error('Failed to load dashboard stats:', err));
    getDashboardTrend().then(setHistory).catch((err) => console.error('Failed to load dashboard trend:', err));
    getHotspots(6).then((data) => setHotspots(data || [])).catch((err) => console.error('Failed to load hotspots:', err));
    try {
      const [accidentRes, trafficRes, anomaliesRes] = await Promise.all([
        getAccidentLayer(), getTrafficLayer(), getAnomalies(5).catch(() => []),
      ]);
      const layerRoads = roadsFromTrafficLayer(trafficRes);
      setRoads(layerRoads.length > 0 ? layerRoads : await getRoads(trafficRes));
      setAccidentFeatures(accidentRes?.features || []);
      setTrafficFeatures(trafficRes?.features || []);
      setAnomalies(anomaliesRes || []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  const countBy = (features, key, fallback = 'UNKNOWN') => {
    const counts = {};
    for (const f of features) {
      const k = (f.properties?.[key] || fallback).toUpperCase();
      counts[k] = (counts[k] || 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  };
  const severityBreakdown = useMemo(() => countBy(accidentFeatures, 'severity'), [accidentFeatures]);
  const congestionBreakdown = useMemo(() => {
    const counts = {};
    for (const f of trafficFeatures) {
      const raw = f.properties?.congestion_level;
      if (!raw || raw === 'UNKNOWN' || raw === 'NOT_PREDICTED') continue;
      const lvl = raw.toUpperCase();
      if (LEVEL_ORDER.includes(lvl)) {
        counts[lvl] = (counts[lvl] || 0) + 1;
      }
    }
    return LEVEL_ORDER.filter((name) => counts[name]).map((name) => ({ name, value: counts[name] }));
  }, [trafficFeatures]);

  const networkStatus = useMemo(() => {
    const counts = {};
    let evaluatedCount = 0;
    for (const r of roads) {
      const raw = r.trafficLevel;
      if (!raw || raw === 'UNKNOWN' || raw === 'NOT_PREDICTED') continue; // Do NOT turn unknown into dummy 'LOW'
      const lvl = raw.toUpperCase();
      if (LEVEL_ORDER.includes(lvl)) {
        counts[lvl] = (counts[lvl] || 0) + 1;
        evaluatedCount++;
      }
    }
    const total = evaluatedCount || 1;
    return {
      total: evaluatedCount,
      totalRoads: roads.length,
      unpredictedCount: Math.max(0, roads.length - evaluatedCount),
      segments: LEVEL_ORDER.filter((l) => counts[l]).map((l) => ({ level: l, count: counts[l], pct: (counts[l] / total) * 100 })),
    };
  }, [roads]);

  const volumeDelta = useMemo(() => {
    if (!history || history.length < 2) return null;
    const last = history[history.length - 1].vehicles;
    const prev = history[history.length - 2].vehicles;
    return prev ? ((last - prev) / prev) * 100 : null;
  }, [history]);

  const topHotspot = hotspots?.[0];

  const insights = useMemo(() => {
    const list = [];
    const high = congestionBreakdown.filter((c) => c.name === 'HIGH' || c.name === 'SEVERE').reduce((s, c) => s + c.value, 0);
    const total = congestionBreakdown.reduce((s, c) => s + c.value, 0);
    if (high > 0 && total > 0) list.push({ tone: 'warn', text: `${Math.round((high / total) * 100)}% of monitored roads are at HIGH or SEVERE congestion right now.` });
    if (topHotspot) list.push({ tone: 'danger', text: `${topHotspot.zone_name || 'Top zone'} is the highest accident hotspot with ${topHotspot.accident_count} recorded accidents.` });
    if (anomalies.length > 0) list.push({ tone: 'warn', text: `${anomalies.length} traffic anomal${anomalies.length === 1 ? 'y has' : 'ies have'} been detected recently. Review the Anomalies page.` });
    if (stats?.accidentAlerts) list.push({ tone: 'danger', text: `${stats.accidentAlerts} severe/fatal accident alert(s) currently require attention.` });
    if (list.length === 0) list.push({ tone: 'ok', text: 'No significant risk signals detected. The system is operating within normal parameters.' });
    return list;
  }, [congestionBreakdown, topHotspot, anomalies, stats]);

  if (isLoading && !stats && roads.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-asphalt-400">Loading dashboard…</p>;
  }

  const dash = '–';
  const fmt = (v) => (v == null ? dash : typeof v === 'number' ? v.toLocaleString() : v);
  const insightDot = { ok: 'bg-signal-green', warn: 'bg-signal-amber', danger: 'bg-signal-red' };
  const axis = isDark ? '#7A828C' : '#64748B';

  return (
    <div className="relative space-y-6">
      <div aria-hidden className="pointer-events-none absolute -top-6 left-1/2 h-[460px] w-[120%] -translate-x-1/2 bg-[radial-gradient(ellipse_at_30%_0%,rgba(62,124,177,0.22),transparent_60%),radial-gradient(ellipse_at_85%_10%,rgba(209,67,67,0.12),transparent_55%)]" />

      {/* Hero: headline + 3D hotspot scene */}
      <div className="relative grid grid-cols-1 items-stretch gap-6 lg:grid-cols-5">
        <div className="flex flex-col justify-center lg:col-span-2">
          <h1 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">
            Smart Traffic Dashboard
          </h1>
          <p className="mt-2 max-w-md text-sm text-slate-600 dark:text-asphalt-300">
            Live congestion, accident risk and road health across every monitored road.
          </p>
          <div className="mt-3 flex items-center gap-2 text-xs text-slate-500 dark:text-asphalt-400">
            <span className="relative flex h-2 w-2">
              <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${stats ? 'animate-ping bg-emerald-400' : 'bg-signal-amber'}`} />
              <span className={`relative inline-flex h-2 w-2 rounded-full ${stats ? 'bg-emerald-500' : 'bg-signal-amber'}`} />
            </span>
            <span className="font-medium">{stats ? 'Live data connected' : 'Backend unavailable'}</span>
            {lastUpdated && <span>Synced {lastUpdated}</span>}
          </div>
          <div className="mt-5 flex items-center gap-2">
            <button
              onClick={() => navigate('/live-map')}
              className="inline-flex items-center gap-1.5 rounded-lg bg-signal-blue px-4 py-2 text-sm font-medium text-white shadow-[0_8px_24px_-8px_#3E7CB1] transition-transform hover:-translate-y-0.5"
            >
              Open live map <ArrowRight size={15} />
            </button>
            <button
              onClick={loadData}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 backdrop-blur transition-colors hover:border-signal-blue/50 disabled:opacity-50 dark:border-asphalt-700 dark:bg-asphalt-900/60 dark:text-asphalt-200"
            >
              <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
              {isLoading ? 'Syncing…' : 'Refresh'}
            </button>
          </div>
          {topHotspot && (
            <div className={`${glass} mt-6 flex items-center gap-3 px-4 py-3`}>
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-signal-red/15 text-signal-red shadow-[0_0_24px_-6px_#D14343]"><Flame size={18} /></span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-asphalt-100">{topHotspot.zone_name || 'Top zone'}</p>
                <p className="text-xs text-slate-500 dark:text-asphalt-400">Highest hotspot · {topHotspot.accident_count} accidents</p>
              </div>
            </div>
          )}
        </div>
        <div className="lg:col-span-3">
          <HotspotScene hotspots={hotspots} isDark={isDark} />
        </div>
      </div>

      {!stats && (
        <div className="rounded-lg border border-signal-amber/30 bg-signal-amber/10 px-4 py-3 text-xs text-signal-amber">
          No live statistics available from the backend API. Please verify the backend connection.
        </div>
      )}

      {/* KPI cards */}
      <div className="relative grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi index={0} icon={Route} label="Active roads" value={fmt(stats?.activeRoads)} hint={stats?.totalRoads ? `of ${stats.totalRoads} registered` : undefined} />
        <Kpi index={1} icon={Flame} tone="warn" label="High traffic" value={fmt(stats?.highTraffic)} hint="roads congested" />
        <Kpi index={2} icon={Gauge} tone="info" label="Avg speed" value={stats?.averageSpeed ? stats.averageSpeed : dash} unit={stats?.averageSpeed ? 'km/h' : undefined} hint="network-wide" />
        <Kpi index={3} icon={Database} label="Traffic records" value={fmt(stats?.totalTrafficRecords)} hint="ingested observations" />
        <Kpi index={4} icon={Siren} tone={stats?.accidentAlerts ? 'danger' : 'neutral'} label="Accident alerts" value={fmt(stats?.accidentAlerts)} hint="need attention" />
        <Kpi index={5} icon={ShieldAlert} tone={stats?.highRiskZones ? 'danger' : 'neutral'} label="High-risk zones" value={fmt(stats?.highRiskZones)} />
        <Kpi index={6} icon={CalendarClock} label="Accidents today" value={fmt(stats?.accidentsToday)} />
        <Kpi index={7} icon={Skull} label="Total accidents" value={fmt(stats?.totalAccidents)} hint="all time" />
      </div>

      {/* Network status bar */}
      {networkStatus.total > 0 && (
        <Panel className="px-5 py-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
            <span className="font-medium text-slate-600 dark:text-asphalt-300">Road network status across {networkStatus.total} segments</span>
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
          <div className="flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-slate-100 dark:bg-asphalt-800">
            {networkStatus.segments.map((seg) => (
              <div key={seg.level} title={`${seg.level}: ${seg.count}`} className="h-full" style={{ width: `${seg.pct}%`, backgroundColor: LEVEL_BAR_COLOR[seg.level], boxShadow: `0 0 12px ${LEVEL_BAR_COLOR[seg.level]}99` }} />
            ))}
          </div>
        </Panel>
      )}

      {/* Tabs */}
      <div className="relative">
        <div role="tablist" aria-label="Dashboard sections" className="flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-asphalt-800">
          {TABS.map((t) => {
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => setActiveTab(t.id)}
                className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? 'border-signal-blue text-signal-blue'
                    : 'border-transparent text-slate-500 hover:text-slate-900 dark:text-asphalt-400 dark:hover:text-asphalt-100'
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div role="tabpanel" className="mt-5">
          {activeTab === 'analytics' && (
            <>
          <Panel title="Traffic and safety analytics" subtitle="Live vehicle volume and accident severity from recorded observations">
            <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
              <div className="p-5 lg:col-span-2">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <BlockLabel>Vehicle volume trend</BlockLabel>
                  <TrendChip delta={volumeDelta} />
                </div>
                {history && history.length > 0 ? (
                  <div className="h-56 [&_.recharts-area-curve]:[filter:drop-shadow(0_6px_8px_rgba(62,124,177,0.7))]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={history}>
                        <defs>
                          <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#5BA3DE" stopOpacity={0.55} />
                            <stop offset="100%" stopColor="#3E7CB1" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke={isDark ? '#282D34' : '#E2E8F0'} strokeOpacity={isDark ? 0.5 : 0.8} vertical={false} />
                        <XAxis dataKey="hour" stroke={axis} fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke={axis} fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ background: isDark ? '#1D2126' : '#fff', border: `1px solid ${isDark ? '#282D34' : '#E2E8F0'}`, borderRadius: 8, fontSize: 12 }}
                          itemStyle={{ color: isDark ? '#E5E7EB' : '#0F172A' }}
                          labelStyle={{ color: axis }}
                          formatter={(v) => [`${Number(v).toLocaleString()} vehicles`, 'Volume']}
                          labelFormatter={(l) => `Time: ${l}`}
                        />
                        <Area type="monotone" dataKey="vehicles" stroke="#5BA3DE" strokeWidth={2.5} fill="url(#volumeFill)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex h-44 flex-col items-center justify-center rounded-md bg-slate-50 p-6 text-center dark:bg-asphalt-950/40">
                    <p className="text-sm font-medium text-slate-600 dark:text-asphalt-300">No traffic trend data yet</p>
                    <p className="mt-1 max-w-sm text-xs text-slate-400 dark:text-asphalt-500">The chart fills in automatically once sensor observations are ingested.</p>
                  </div>
                )}
              </div>
              <div className="p-5">
                <BlockLabel>Accidents by severity</BlockLabel>
                <Donut data={severityBreakdown} isDark={isDark} />
              </div>
            </div>
          </Panel>

            </>
          )}
          {activeTab === 'risk' && (
            <>
          <Panel title="Risk and congestion" subtitle="Where problems concentrate and what needs attention">
            <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
              <div className="p-5">
                <BlockLabel>Congestion by level</BlockLabel>
                <Donut data={congestionBreakdown} isDark={isDark} />
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

            </>
          )}
          {activeTab === 'roads' && (
            <>
          <section>
            <div className="mb-3 flex items-baseline justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-asphalt-100">Road status</h3>
                <p className="text-xs text-slate-500 dark:text-asphalt-400">Authentic AI traffic predictions from machine learning model</p>
              </div>
              <span className="rounded bg-signal-blue/10 px-2 py-0.5 text-xs font-medium text-signal-blue">
                AI Model Predictions
              </span>
            </div>
            <DataTable
              label="roads"
              columns={[
                { key: 'name', header: 'Road' },
                {
                  key: 'vehicleCount',
                  header: 'Predicted Vehicles',
                  render: (row) =>
                    row.vehicleCount != null && row.vehicleCount !== '-'
                      ? Number(row.vehicleCount).toLocaleString()
                      : '—',
                },
                { key: 'avgSpeed', header: 'Avg speed' },
                { key: 'weather', header: 'Weather' },
                {
                  key: 'trafficLevel',
                  header: 'Congestion Level',
                  render: (row) => (
                    <LevelBadge
                      level={row.trafficLevel}
                      colorMap={TRAFFIC_LEVEL_COLOR}
                      fallbackText="Not Predicted"
                    />
                  ),
                },
                {
                  key: 'confidenceScore',
                  header: 'AI Confidence',
                  render: (row) =>
                    row.confidenceScore != null ? (
                      <span className="font-medium text-slate-700 dark:text-asphalt-200">
                        {Number(row.confidenceScore).toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-slate-400 dark:text-asphalt-500">—</span>
                    ),
                },
              ]}
              rows={roads}
              emptyMessage="No road segments found in the database. Add roads or connect live traffic sensors to view records."
            />
          </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
