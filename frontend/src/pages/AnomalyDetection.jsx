import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import * as trafficService from '../api/trafficService';

export default function AnomalyDetection() {
  const [anomalies, setAnomalies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    trafficService.getAnomalies().then((data) => {
      setAnomalies(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Scanning for anomalies…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        Roads where observed traffic volume deviates sharply from the expected baseline.
      </p>
      <DataTable
        columns={[
          { key: 'roadName', header: 'Road' },
          { key: 'expected', header: 'Expected (veh/hr)' },
          { key: 'observed', header: 'Observed (veh/hr)' },
          {
            key: 'ratio',
            header: 'Deviation',
            render: (row) => `${(row.observed / row.expected).toFixed(1)}×`,
          },
          { key: 'possibleCause', header: 'Likely cause' },
        ]}
        rows={anomalies}
        emptyMessage="No anomalies detected."
      />
    </div>
  );
}
