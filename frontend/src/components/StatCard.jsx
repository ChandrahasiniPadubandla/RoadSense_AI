import React from 'react';

export default function StatCard({ label, value, accent = 'text-asphalt-100' }) {
  return (
    <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 px-5 py-4">
      <p className="text-xs uppercase tracking-wide text-asphalt-400">{label}</p>
      <p className={`data-num mt-2 text-3xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}
