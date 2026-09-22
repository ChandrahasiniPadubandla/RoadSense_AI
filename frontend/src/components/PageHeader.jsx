import React from 'react';

/**
 * Shared page header used across dashboard pages, styled to match the
 * landing page's voice: a small uppercase "eyebrow" label, a bold
 * tight-tracking title, and an optional subtitle/description.
 */
export default function PageHeader({ eyebrow, title, subtitle, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4 dark:border-asphalt-800">
      <div>
        {eyebrow && (
          <p className="mb-1 font-mono text-[11px] font-bold uppercase tracking-widest text-signal-blue">
            {eyebrow}
          </p>
        )}
        <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
