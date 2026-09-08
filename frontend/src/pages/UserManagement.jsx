import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import { ROLE_LABELS } from '../utils/constants';
import * as userService from '../api/userService';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    userService.getUsers().then((data) => {
      setUsers(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading users…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">{users.length} system users.</p>
      <DataTable
        columns={[
          { key: 'name', header: 'Name' },
          { key: 'email', header: 'Email' },
          { key: 'phone', header: 'Phone', render: (row) => row.phone || '—' },
          {
            key: 'role',
            header: 'Role',
            render: (row) => ROLE_LABELS[row.role] || row.role,
          },
          {
            key: 'isActive',
            header: 'Status',
            render: (row) => (row.isActive ? 'Active' : 'Disabled'),
          },
        ]}
        rows={users}
      />
    </div>
  );
}
