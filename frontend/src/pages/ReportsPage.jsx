import React, { useRef, useState } from 'react';
import { Download, FileText, Loader2, RefreshCw, Calendar, CheckCircle2, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR, RISK_LEVEL_COLOR, SEVERITY_COLOR } from '../utils/constants';
import { getReportPreview, getReportPage, downloadReportCsv } from '../api_services';

// Backend caps a CSV export at 10,000 rows (see backend/app/routers/reports.py).
const CSV_EXPORT_LIMIT = 10000;

const fmtDate = (v) => (v ? new Date(v).toLocaleString() : '—');
const fmtVal = (v) => (v === null || v === undefined || v === '' ? '—' : v);
const upper = (v) => (v || 'UNKNOWN').toString().toUpperCase();

/**
 * Report catalogue. Each entry mirrors a report_type supported by the backend
 * (GET /api/reports?report_type=…) and describes the columns of its JSON rows.
 */
const REPORTS = [
  {
    value: 'summary',
    label: 'System Summary',
    description: 'Key operational figures across roads, traffic, accidents and hotspots.',
    supportsDates: false,
    paginated: false,
    rowId: (_r, i) => i,
    columns: [
      { key: 'metric', header: 'Metric' },
      { key: 'value', header: 'Value', render: (r) => <span className="data-num font-semibold">{fmtVal(r.value)}</span> },
      { key: 'notes', header: 'Notes' },
    ],
  },
  {
    value: 'accidents',
    label: 'Accidents',
    description: 'Recorded accidents with severity, casualties, road and weather conditions.',
    supportsDates: true,
    paginated: true,
    rowId: (r) => r.accident_id,
    columns: [
      { key: 'road_name', header: 'Road' },
      { key: 'accident_time', header: 'Date & time', render: (r) => fmtDate(r.accident_time) },
      { key: 'severity', header: 'Severity', render: (r) => <LevelBadge level={upper(r.severity)} colorMap={SEVERITY_COLOR} /> },
      { key: 'fatalities', header: 'Fatalities', render: (r) => fmtVal(r.fatalities) },
      { key: 'injuries', header: 'Injuries', render: (r) => fmtVal(r.injuries) },
      { key: 'vehicle_count', header: 'Vehicles', render: (r) => fmtVal(r.vehicle_count) },
      { key: 'weather_condition', header: 'Weather', render: (r) => fmtVal(r.weather_condition) },
      { key: 'road_condition', header: 'Road condition', render: (r) => fmtVal(r.road_condition) },
    ],
  },
  {
    value: 'traffic',
    label: 'Traffic Observations',
    description: 'Vehicle counts, speeds, density and congestion per road over time.',
    supportsDates: true,
    paginated: true,
    rowId: (r) => r.traffic_id,
    columns: [
      { key: 'road_name', header: 'Road' },
      { key: 'timestamp', header: 'Observed', render: (r) => fmtDate(r.timestamp) },
      { key: 'vehicle_count', header: 'Vehicles', render: (r) => fmtVal(r.vehicle_count) },
      { key: 'average_speed_kmh', header: 'Avg speed', render: (r) => (r.average_speed_kmh != null ? `${r.average_speed_kmh.toFixed(1)} km/h` : '—') },
      { key: 'traffic_density', header: 'Density', render: (r) => (r.traffic_density != null ? `${r.traffic_density.toFixed(1)}%` : '—') },
      { key: 'congestion_level', header: 'Congestion', render: (r) => <LevelBadge level={upper(r.congestion_level)} colorMap={TRAFFIC_LEVEL_COLOR} /> },
      { key: 'weather_condition', header: 'Weather', render: (r) => fmtVal(r.weather_condition) },
    ],
  },
  {
    value: 'hotspots',
    label: 'Accident Hotspots',
    description: 'Zones ranked by accident count with calculated risk score and level.',
    supportsDates: false,
    paginated: true,
    rowId: (r) => r.hotspot_id,
    columns: [
      { key: 'zone_name', header: 'Zone' },
      { key: 'accident_count', header: 'Accidents', render: (r) => fmtVal(r.accident_count) },
      { key: 'risk_score', header: 'Risk score', render: (r) => fmtVal(r.risk_score) },
      { key: 'risk_level', header: 'Risk level', render: (r) => <LevelBadge level={upper(r.risk_level)} colorMap={RISK_LEVEL_COLOR} /> },
      { key: 'calculated_at', header: 'Last calculated', render: (r) => fmtDate(r.calculated_at) },
    ],
  },
  {
    value: 'predictions',
    label: 'ML Predictions',
    description: 'Latest traffic-congestion and accident-risk predictions for every active road.',
    supportsDates: false,
    paginated: true,
    rowId: (r) => r.road_id,
    columns: [
      { key: 'road_name', header: 'Road' },
      { key: 'road_type', header: 'Type', render: (r) => fmtVal(r.road_type) },
      { key: 'predicted_congestion', header: 'Predicted congestion', render: (r) => <LevelBadge level={upper(r.predicted_congestion)} colorMap={TRAFFIC_LEVEL_COLOR} /> },
      { key: 'predicted_vehicles', header: 'Predicted vehicles', render: (r) => fmtVal(r.predicted_vehicles) },
      { key: 'accident_risk_level', header: 'Accident risk', render: (r) => <LevelBadge level={upper(r.accident_risk_level)} colorMap={RISK_LEVEL_COLOR} /> },
      { key: 'accident_risk_pct', header: 'Risk %', render: (r) => (r.accident_risk_pct != null ? `${Number(r.accident_risk_pct).toFixed(1)}%` : '—') },
      { key: 'last_evaluated', header: 'Last evaluated', render: (r) => fmtDate(r.last_evaluated) },
    ],
  },
];

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white dark:disabled:bg-asphalt-900 dark:disabled:text-asphalt-500';
const labelClass = 'mb-1 block text-xs font-medium text-slate-600 dark:text-asphalt-300';

const toISODate = (d) => {
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
};
const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return toISODate(d);
};

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'All time', days: null },
];

function describeRange(startDate, endDate) {
  if (!startDate && !endDate) return 'All time';
  if (startDate && endDate) return `${startDate} → ${endDate}`;
  return startDate ? `From ${startDate}` : `Up to ${endDate}`;
}

export default function ReportsPage() {
  // ---- form (what the user is configuring) --------------------------------
  const [reportType, setReportType] = useState('summary');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // ---- generated report (a snapshot of the parameters that were run) ------
  const [status, setStatus] = useState('idle'); // idle | generating | ready | error
  const [generated, setGenerated] = useState(null); // { type, startDate, endDate, generatedAt, generatedBy }
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [isPageLoading, setIsPageLoading] = useState(false);

  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);

  const config = REPORTS.find((r) => r.value === reportType);
  const generatedConfig = generated ? REPORTS.find((r) => r.value === generated.type) : null;

  const formMatchesGenerated =
    generated &&
    generated.type === reportType &&
    generated.startDate === (config.supportsDates ? startDate : '') &&
    generated.endDate === (config.supportsDates ? endDate : '');

  function errorMessage(err, fallback) {
    if (err.response?.status === 403) return 'You do not have permission to generate this report.';
    const detail = err.response?.data?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }

  function applyPreset(days) {
    setStartDate(days == null ? '' : daysAgo(days));
    setEndDate(days == null ? '' : toISODate(new Date()));
  }

  // Fetch one page of the generated report (server-side pagination).
  async function fetchPage(snapshot, nextPage, nextSize) {
    const current = ++requestId.current;
    setIsPageLoading(true);
    setError('');
    try {
      const data = await getReportPage(snapshot.type, {
        startDate: snapshot.startDate,
        endDate: snapshot.endDate,
        page: nextPage,
        pageSize: nextSize,
      });
      if (current !== requestId.current) return;
      setRows(data.items || []);
      setTotal(data.total ?? 0);
      setPage(data.page ?? nextPage);
    } catch (err) {
      if (current !== requestId.current) return;
      setError(errorMessage(err, 'Could not load this page of the report.'));
    } finally {
      if (current === requestId.current) setIsPageLoading(false);
    }
  }

  async function handleGenerate() {
    const snapshot = {
      type: reportType,
      startDate: config.supportsDates ? startDate : '',
      endDate: config.supportsDates ? endDate : '',
    };

    if (snapshot.startDate && snapshot.endDate && snapshot.startDate > snapshot.endDate) {
      setError('The "From" date must be on or before the "To" date.');
      return;
    }

    const current = ++requestId.current;
    setStatus('generating');
    setError('');

    try {
      if (config.paginated) {
        const data = await getReportPage(snapshot.type, { ...snapshot, page: 1, pageSize });
        if (current !== requestId.current) return;
        setRows(data.items || []);
        setTotal(data.total ?? 0);
        setPage(1);
        setGenerated({ ...snapshot, generatedAt: new Date().toISOString(), generatedBy: null });
      } else {
        // System summary: a small fixed KPI list, returned in one response.
        const data = await getReportPreview(snapshot.type, snapshot);
        if (current !== requestId.current) return;
        const list = (data.summary || []).map((r, i) => ({ ...r, id: i }));
        setRows(list);
        setTotal(list.length);
        setPage(1);
        setGenerated({
          ...snapshot,
          generatedAt: data.generated_at || new Date().toISOString(),
          generatedBy: data.generated_by || null,
        });
      }
      setStatus('ready');
    } catch (err) {
      if (current !== requestId.current) return;
      setStatus('error');
      setError(errorMessage(err, 'Could not generate this report. Please check the backend connection and try again.'));
    }
  }

  async function handleDownload() {
    if (!generated) return;
    setIsDownloading(true);
    setError('');
    try {
      await downloadReportCsv(generated.type, {
        startDate: generated.startDate,
        endDate: generated.endDate,
        limit: CSV_EXPORT_LIMIT,
      });
    } catch (err) {
      setError(errorMessage(err, 'Could not download this report.'));
    } finally {
      setIsDownloading(false);
    }
  }

  const isGenerating = status === 'generating';
  const tableRows =
    generatedConfig?.paginated
      ? rows.map((r, i) => ({ ...r, id: generatedConfig.rowId(r, i) ?? i }))
      : rows;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Analytics"
        title="Reports"
        subtitle="Generate and export system reports — accidents, traffic, hotspots and ML predictions — straight from the database."
      />

      {/* ------------------------------------------------------------------ */}
      {/* Configuration                                                       */}
      {/* ------------------------------------------------------------------ */}
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-asphalt-700 dark:bg-asphalt-900">
        <div className="grid grid-cols-1 divide-y divide-slate-100 dark:divide-asphalt-800 lg:grid-cols-5 lg:divide-x lg:divide-y-0">
          {/* Report categories */}
          <div className="p-5 lg:col-span-3">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-asphalt-400">
              1 · Report type
            </p>
            <div role="radiogroup" aria-label="Report type" className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {REPORTS.map((r) => {
                const active = r.value === reportType;
                return (
                  <button
                    key={r.value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    disabled={isGenerating}
                    onClick={() => setReportType(r.value)}
                    className={`rounded-md border px-3 py-2.5 text-left transition-colors disabled:opacity-60 ${
                      active
                        ? 'border-signal-blue bg-signal-blue/5'
                        : 'border-slate-200 hover:border-signal-blue/40 dark:border-asphalt-700'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className={`h-2 w-2 rounded-full ${active ? 'bg-signal-blue' : 'bg-slate-300 dark:bg-asphalt-600'}`}
                      />
                      <span className={`text-sm font-semibold ${active ? 'text-signal-blue' : 'text-slate-800 dark:text-asphalt-100'}`}>
                        {r.label}
                      </span>
                    </span>
                    <span className="mt-1 block pl-4 text-xs text-slate-500 dark:text-asphalt-400">{r.description}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Filters + action */}
          <div className="flex flex-col p-5 lg:col-span-2">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-asphalt-400">
              2 · Date range
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass} htmlFor="report-from">From</label>
                <input
                  id="report-from"
                  type="date"
                  value={startDate}
                  max={endDate || undefined}
                  disabled={!config.supportsDates || isGenerating}
                  onChange={(e) => setStartDate(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="report-to">To</label>
                <input
                  id="report-to"
                  type="date"
                  value={endDate}
                  min={startDate || undefined}
                  disabled={!config.supportsDates || isGenerating}
                  onChange={(e) => setEndDate(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            {config.supportsDates ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    disabled={isGenerating}
                    onClick={() => applyPreset(p.days)}
                    className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 transition-colors hover:border-signal-blue/50 hover:text-signal-blue disabled:opacity-50 dark:border-asphalt-700 dark:text-asphalt-300"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-3 flex items-start gap-1.5 text-xs text-slate-500 dark:text-asphalt-400">
                <Calendar size={13} className="mt-0.5 shrink-0" />
                This report is a current snapshot, so a date range does not apply.
              </p>
            )}

            <div className="mt-auto pt-5">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={isGenerating}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-signal-blue px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
              >
                {isGenerating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Generating…
                  </>
                ) : (
                  <>
                    <FileText size={16} /> Generate report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Status / errors                                                     */}
      {/* ------------------------------------------------------------------ */}
      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {status === 'idle' && (
        <div className="rounded-lg border border-dashed border-slate-300 px-6 py-12 text-center dark:border-asphalt-700">
          <FileText size={28} className="mx-auto text-slate-300 dark:text-asphalt-600" />
          <p className="mt-3 text-sm font-medium text-slate-700 dark:text-asphalt-200">No report generated yet</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-asphalt-400">
            Choose a report type{config.supportsDates ? ' and date range' : ''}, then press <strong>Generate report</strong>.
          </p>
        </div>
      )}

      {isGenerating && (
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-5 py-6 text-sm text-slate-600 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-300">
          <Loader2 size={18} className="animate-spin text-signal-blue" />
          Generating {config.label.toLowerCase()} report…
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Generated report                                                    */}
      {/* ------------------------------------------------------------------ */}
      {generated && generatedConfig && !isGenerating && status !== 'idle' && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-signal-green" />
                <h3 className="text-base font-bold text-slate-900 dark:text-asphalt-100">{generatedConfig.label} report</h3>
              </div>
              <dl className="mt-1.5 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500 dark:text-asphalt-400">
                <div className="flex gap-1">
                  <dt>Generated</dt>
                  <dd className="font-medium text-slate-700 dark:text-asphalt-200">{fmtDate(generated.generatedAt)}</dd>
                </div>
                {generated.generatedBy && (
                  <div className="flex gap-1">
                    <dt>By</dt>
                    <dd className="font-medium text-slate-700 dark:text-asphalt-200">{generated.generatedBy}</dd>
                  </div>
                )}
                {generatedConfig.supportsDates && (
                  <div className="flex gap-1">
                    <dt>Range</dt>
                    <dd className="font-medium text-slate-700 dark:text-asphalt-200">
                      {describeRange(generated.startDate, generated.endDate)}
                    </dd>
                  </div>
                )}
                <div className="flex gap-1">
                  <dt>Records</dt>
                  <dd className="data-num font-medium text-slate-700 dark:text-asphalt-200">{total.toLocaleString()}</dd>
                </div>
              </dl>
              {!formMatchesGenerated && (
                <p className="mt-2 flex items-center gap-1.5 text-xs text-signal-amber">
                  <RefreshCw size={12} />
                  Settings changed since this report was generated — press Generate report to refresh.
                </p>
              )}
            </div>

            <div className="text-right">
              <button
                type="button"
                onClick={handleDownload}
                disabled={isDownloading}
                className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-signal-blue/60 hover:text-signal-blue disabled:opacity-60 dark:border-asphalt-600 dark:bg-asphalt-900 dark:text-asphalt-200"
              >
                {isDownloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                {isDownloading ? 'Preparing CSV…' : 'Download CSV'}
              </button>
              {generatedConfig.paginated && total > CSV_EXPORT_LIMIT && (
                <p className="mt-1 text-[11px] text-slate-400 dark:text-asphalt-500">
                  CSV contains the {CSV_EXPORT_LIMIT.toLocaleString()} most recent records.
                </p>
              )}
            </div>
          </div>

          <DataTable
            columns={generatedConfig.columns}
            rows={tableRows}
            label={generatedConfig.value === 'summary' ? 'metrics' : 'records'}
            paginate={false}
            pagination={
              generatedConfig.paginated
                ? {
                    page,
                    pageSize,
                    total,
                    loading: isPageLoading,
                    onPageChange: (p) => fetchPage(generated, p, pageSize),
                    onPageSizeChange: (s) => {
                      setPageSize(s);
                      fetchPage(generated, 1, s);
                    },
                  }
                : null
            }
            emptyMessage="No records found for this report type and date range."
          />
        </section>
      )}
    </div>
  );
}
