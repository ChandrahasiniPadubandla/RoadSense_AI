import React from 'react';

export default function StatCard({ label, value, accent = 'text-slate-900 dark:text-asphalt-100', icon }) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm transition-shadow hover:shadow-md dark:border-asphalt-700 dark:bg-asphalt-900">
      <span className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-signal-blue/0 via-signal-blue/70 to-signal-blue/0 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-asphalt-400">{label}</p>
        {icon && (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm dark:bg-asphalt-800">
            {icon}
          </span>
        )}
      </div>
      <p className={`data-num mt-2 text-3xl font-extrabold tracking-tight ${accent}`}>{value}</p>
    </div>
  );
}
