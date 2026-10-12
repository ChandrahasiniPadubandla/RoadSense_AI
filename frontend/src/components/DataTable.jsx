import React, { useEffect, useMemo, useState } from 'react';
import Pagination from './Pagination';

/**
 * columns: [{ key, header, render?(row) }]
 * rows:    array of objects
 *
 * Pagination
 * ----------
 * 1. Client-side (default): `rows` is the full, already-filtered dataset and the
 *    table slices it into pages. Only the current page is rendered to the DOM.
 *    The page resets to 1 automatically whenever the dataset changes (different
 *    length / first / last row), or when `resetKey` changes.
 *
 * 2. Server-side: pass `pagination={{ page, pageSize, total, onPageChange,
 *    onPageSizeChange, loading }}`. `rows` must then contain ONLY the current
 *    page as returned by the backend, and the parent owns the page state.
 *
 * Pass `paginate={false}` to render every row with no footer.
 */
export default function DataTable({
  columns,
  rows,
  emptyMessage = 'No records found.',
  paginate = true,
  pagination = null,
  resetKey = undefined,
  defaultPageSize = 10,
  label = 'records',
}) {
  const serverSide = Boolean(pagination);
  const allRows = rows || [];

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);

  // Signature of the current dataset – changes when filters/search alter the result set.
  const signature = useMemo(() => {
    if (serverSide) return '';
    const first = allRows[0];
    const last = allRows[allRows.length - 1];
    return `${allRows.length}|${first?.id ?? ''}|${last?.id ?? ''}`;
  }, [allRows, serverSide]);

  useEffect(() => {
    if (!serverSide) setPage(1);
  }, [signature, resetKey, serverSide]);

  const total = serverSide ? pagination.total : allRows.length;
  const activePage = serverSide ? pagination.page : page;
  const activeSize = serverSide ? pagination.pageSize : pageSize;

  const totalPages = Math.max(1, Math.ceil(total / activeSize));
  const safePage = Math.min(activePage, totalPages);

  const visibleRows = useMemo(() => {
    if (serverSide || !paginate) return allRows;
    const start = (safePage - 1) * activeSize;
    return allRows.slice(start, start + activeSize);
  }, [allRows, serverSide, paginate, safePage, activeSize]);

  if (!allRows.length && !(serverSide && pagination.loading)) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-400">
        {emptyMessage}
      </div>
    );
  }

  const showFooter = serverSide || paginate;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-asphalt-700 dark:bg-asphalt-900">
      <div className={`overflow-x-auto ${serverSide && pagination.loading ? 'opacity-60 transition-opacity' : ''}`}>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-500 dark:border-asphalt-700 dark:bg-asphalt-950/40 dark:text-asphalt-400">
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 font-medium">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, idx) => (
              <tr
                key={row.id ?? `${safePage}-${idx}`}
                className="border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-asphalt-800 dark:hover:bg-asphalt-800/60"
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-slate-700 dark:text-asphalt-200">
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showFooter && (
        <Pagination
          page={safePage}
          pageSize={activeSize}
          total={total}
          label={label}
          disabled={serverSide && pagination.loading}
          onPageChange={(p) => (serverSide ? pagination.onPageChange(p) : setPage(p))}
          onPageSizeChange={(s) => {
            if (serverSide) {
              pagination.onPageSizeChange?.(s);
            } else {
              setPageSize(s);
              setPage(1);
            }
          }}
        />
      )}
    </div>
  );
}
