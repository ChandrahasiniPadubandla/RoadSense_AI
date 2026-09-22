import React, { useState } from 'react';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import { getReportPreview, downloadReportCsv } from '../api_services';

const REPORT_TYPES = [
  { value: 'summary', label: 'System Summary' },
  { value: 'accidents', label: 'Accidents' },
  { value: 'traffic', label: 'Traffic Observations' },
  { value: 'hotspots', label: 'Accident Hotspots' },
  { value: 'predictions', label: 'ML Predictions' },
];

const inputClass =
  'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-white';
const labelClass = 'mb-1 block text-xs font-medium text-slate-600 dark:text-asphalt-300';

function humanizeKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState('summary');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [preview, setPreview] = useState(null); // { rows, columns, meta }
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');

  async function handlePreview() {
    setIsLoading(true);
    setError('');
    setPreview(null);
    try {
      const data = await getReportPreview(reportType, { startDate, endDate });

      if (reportType === 'summary') {
        setPreview({
          meta: { generated_at: data.generated_at, generated_by: data.generated_by },
          columns: [
            { key: 'metric', header: 'Metric' },
            { key: 'value', header: 'Value' },
            { key: 'notes', header: 'Notes' },
          ],
          rows: (data.summary || []).map((r, i) => ({ ...r, id: i })),
        });
      } else {
        const rows = Array.isArray(data) ? data : [];
        const columns = rows.length > 0 ? Object.keys(rows[0]).map((k) => ({ key: k, header: humanizeKey(k) })) : [];
        setPreview({
          meta: { count: rows.length },
          columns,
          rows: rows.map((r, i) => ({ ...r, id: r.accident_id || r.traffic_id || r.hotspot_id || r.prediction_id || i })),
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not generate this report. You may not have permission, or no data matches these filters.');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDownload() {
    setIsDownloading(true);
    setError('');
    try {
      await downloadReportCsv(reportType, { startDate, endDate });
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not download this report.');
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Analytics"
        title="Reports"
        subtitle="Generate and export real system reports — accidents, traffic, hotspots, and ML predictions, straight from the database."
      />

      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-asphalt-700 dark:bg-asphalt-900">
        <div className="min-w-[180px]">
          <label className={labelClass}>Report type</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)} className={inputClass}>
            {REPORT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>From</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label className={labelClass}>To</label>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
        </div>
        <button
          onClick={handlePreview}
          disabled={isLoading}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-signal-blue/50 hover:text-signal-blue disabled:opacity-50 dark:border-asphalt-600 dark:text-asphalt-200"
        >
          {isLoading ? 'Loading…' : 'Preview'}
        </button>
        <button
          onClick={handleDownload}
          disabled={isDownloading}
          className="rounded-md bg-signal-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isDownloading ? 'Preparing CSV…' : '⬇ Download CSV'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-signal-red/30 bg-signal-red/10 px-4 py-3 text-xs text-signal-red">{error}</div>
      )}

      {preview && (
        <div className="space-y-2">
          {preview.meta?.generated_at && (
            <p className="text-xs text-slate-500 dark:text-asphalt-400">
              Generated {new Date(preview.meta.generated_at).toLocaleString()}
              {preview.meta.generated_by ? ` by ${preview.meta.generated_by}` : ''}
            </p>
          )}
          {preview.meta?.count !== undefined && (
            <p className="text-xs text-slate-500 dark:text-asphalt-400">{preview.meta.count} record(s) matched.</p>
          )}
          <DataTable
            columns={preview.columns}
            rows={preview.rows}
            emptyMessage="No records found for this report type and date range."
          />
        </div>
      )}

      {!preview && !isLoading && !error && (
        <p className="text-sm text-slate-500 dark:text-asphalt-400">
          Choose a report type and click Preview to see the data here, or Download CSV to save it directly.
        </p>
      )}
    </div>
  );
}
