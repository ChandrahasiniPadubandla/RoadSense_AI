import React from 'react';
import DataTable from '../components/DataTable';
import { mockUsers } from '../mock/mockData';
import { ROLE_LABELS } from '../utils/constants';

// NOTE: wire this to GET/POST/PATCH /users once the backend is ready —
// see README "Connecting the backend" for the exact contract to implement.
export default function UserManagement() {
  const rows = mockUsers.map(({ password: _pw, ...rest }) => rest);

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        {rows.length} system users. Read-only preview until the backend endpoint is connected.
      </p>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'email', header: 'Email' },
          {
            key: 'role',
            header: 'Role',
            render: (row) => ROLE_LABELS[row.role] || row.role,
          },
        ]}
        rows={rows}
      />
    </div>
  );
}
