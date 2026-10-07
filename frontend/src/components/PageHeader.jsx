import React from 'react';

/**
 * Shared page header used across dashboard pages.
 * Stays at the top of the scrollable page area.
 */
export default function PageHeader({
  eyebrow,
  title,
  subtitle,
  action,
}) {
  return (
    <div
      className="
        sticky
        top-0
        z-40
        -mx-6
        mb-6
        border-b
        border-slate-200
        bg-slate-50
        px-6
        py-4
        shadow-sm
        dark:border-asphalt-800
        dark:bg-asphalt-950
      "
    >
      <div className="flex flex-wrap items-start justify-between gap-4">

        {/* LEFT SIDE */}

        <div>
          {eyebrow && (
            <p className="mb-1 font-mono text-[11px] font-bold uppercase tracking-widest text-signal-blue">
              {eyebrow}
            </p>
          )}
           <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-asphalt-100">
            {title}
          </h2>


          {subtitle && (
            <p className="mt-1 text-sm text-slate-500 dark:text-asphalt-400">
              {subtitle}
            </p>
          )}
        </div>

        {/* RIGHT SIDE */}

        {action && (
          <div className="shrink-0">
            {action}
          </div>
        )}

      </div>
    </div>
  );
}