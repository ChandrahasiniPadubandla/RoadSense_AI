import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import * as trafficService from '../api/trafficService';

export default function TrafficPrediction() {
  const [predictions, setPredictions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    trafficService.getCongestionPredictions().then((data) => {
      setPredictions(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Running prediction model…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        ML-generated congestion forecasts for the next prediction window.
      </p>
      <DataTable
        columns={[
          { key: 'roadName', header: 'Road' },
          {
            key: 'window',
            header: 'Predicted window',
            render: (row) => `${row.windowStart} – ${row.windowEnd}`,
          },
          {
            key: 'confidence',
            header: 'Confidence',
            render: (row) => `${Math.round(row.confidence * 100)}%`,
          },
          {
            key: 'predictedLevel',
            header: 'Predicted level',
            render: (row) => (
              <LevelBadge level={row.predictedLevel} colorMap={TRAFFIC_LEVEL_COLOR} />
            ),
          },
        ]}
        rows={predictions}
        emptyMessage="No congestion predicted right now."
      />
    </div>
  );
}
