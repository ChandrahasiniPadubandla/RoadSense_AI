import React from 'react';

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];


export function getPageItems(page, totalPages, siblings = 1) {
  const maxNoEllipsis = siblings * 2 + 5;
  if (totalPages <= maxNoEllipsis) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const edgeSpan = siblings * 2 + 3; // pages shown when the current page is near either end
  if (page <= siblings + 3) {
    return [...Array.from({ length: edgeSpan }, (_, i) => i + 1), '…', totalPages];
  }
  if (page >= totalPages - siblings - 2) {
    return [1, '…', ...Array.from({ length: edgeSpan }, (_, i) => totalPages - edgeSpan + 1 + i)];
  }

  const left = Math.max(page - siblings, 2);
  const right = Math.min(page + siblings, totalPages - 1);
  const items = [1];

  if (left > 2) items.push('…');
  for (let p = left; p <= right; p += 1) items.push(p);
  if (right < totalPages - 1) items.push('…');
  items.push(totalPages);

  return items;
}

const btnBase =
  'inline-flex h-8 min-w-[2rem] items-center justify-center rounded-md px-2 text-xs font-medium transition-colors';
const btnIdle =
  'text-slate-600 hover:bg-slate-100 dark:text-asphalt-300 dark:hover:bg-asphalt-800';
const btnActive = 'bg-signal-blue text-white';
const btnDisabled = 'cursor-not-allowed text-slate-300 dark:text-asphalt-600';


export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = PAGE_SIZE_OPTIONS,
  disabled = false,
  label = 'records',
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const items = getPageItems(page, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-xs text-slate-500 dark:border-asphalt-700 dark:text-asphalt-400">
      <p>
        Showing{' '}
        <span className="data-num font-semibold text-slate-700 dark:text-asphalt-200">
          {from}–{to}
        </span>{' '}
        of{' '}
        <span className="data-num font-semibold text-slate-700 dark:text-asphalt-200">
          {total.toLocaleString()}
        </span>{' '}
        {label}
      </p>

      <div className="flex flex-wrap items-center gap-4">
        {onPageSizeChange && (
          <label className="flex items-center gap-2">
            <span>Rows per page</span>
            <select
              value={pageSize}
              disabled={disabled}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-950 dark:text-asphalt-200"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}

        {totalPages > 1 && (
          <nav className="flex items-center gap-1" aria-label="Pagination">
            <button
              type="button"
              disabled={disabled || page <= 1}
              onClick={() => onPageChange(page - 1)}
              className={`${btnBase} ${page <= 1 || disabled ? btnDisabled : btnIdle}`}
            >
              Previous
            </button>

            {items.map((item, idx) =>
              item === '…' ? (
                <span key={`gap-${idx}`} className="px-1 text-slate-400 dark:text-asphalt-500">
                  …
                </span>
              ) : (
                <button
                  key={item}
                  type="button"
                  disabled={disabled}
                  aria-current={item === page ? 'page' : undefined}
                  onClick={() => onPageChange(item)}
                  className={`${btnBase} data-num ${item === page ? btnActive : btnIdle}`}
                >
                  {item}
                </button>
              )
            )}

            <button
              type="button"
              disabled={disabled || page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className={`${btnBase} ${page >= totalPages || disabled ? btnDisabled : btnIdle}`}
            >
              Next
            </button>
          </nav>
        )}
      </div>
    </div>
  );
}
