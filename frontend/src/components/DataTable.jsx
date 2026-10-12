import React from 'react';

/**
 * columns: [{ key, header, render?(row) }]
 * rows: array of objects
 */
export default function DataTable({ columns, rows, emptyMessage = 'No records found.' }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-400">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white dark:border-asphalt-700 dark:bg-asphalt-900">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-asphalt-700 dark:text-asphalt-400">
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-3 font-medium">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={row.id || idx}
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
  );
}
