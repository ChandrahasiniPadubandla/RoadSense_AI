import React from 'react';

export default function StatCard({ label, value, accent = 'text-slate-900 dark:text-asphalt-100' }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 dark:border-asphalt-700 dark:bg-asphalt-900">
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-asphalt-400">{label}</p>
      <p className={`data-num mt-2 text-3xl font-extrabold tracking-tight ${accent}`}>{value}</p>
    </div>
  );
}
