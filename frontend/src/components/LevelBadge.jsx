import React from 'react';

export default function LevelBadge({ level, colorMap, fallbackText = 'Not Available' }) {
  if (!level || level === 'UNKNOWN' || level === 'NOT_PREDICTED') {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-500 dark:border-asphalt-700 dark:bg-asphalt-800 dark:text-asphalt-400">
        {level === 'NOT_PREDICTED' ? 'Not Predicted' : level === 'UNKNOWN' ? 'Unknown' : fallbackText}
      </span>
    );
  }
  const classes = colorMap[level] || 'text-slate-500 border-slate-200 bg-slate-50 dark:border-asphalt-700 dark:bg-asphalt-800 dark:text-asphalt-400';
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${classes}`}
    >
      {level}
    </span>
  );
}

