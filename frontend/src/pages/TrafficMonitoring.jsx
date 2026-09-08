import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import * as trafficService from '../api/trafficService';

export default function TrafficMonitoring() {
  const [roads, setRoads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    trafficService.getRoads().then((data) => {
      setRoads(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading roads…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        {roads.length} monitored road segments · updated live from sensor feeds
      </p>
      <DataTable
        columns={[
          { key: 'id', header: 'Road ID' },
          { key: 'name', header: 'Location' },
          { key: 'vehicleCount', header: 'Vehicle count' },
          { key: 'capacity', header: 'Capacity' },
          { key: 'avgSpeed', header: 'Avg speed (km/h)' },
          { key: 'weather', header: 'Weather' },
          {
            key: 'trafficLevel',
            header: 'Level',
            render: (row) => (
              <LevelBadge level={row.trafficLevel} colorMap={TRAFFIC_LEVEL_COLOR} />
            ),
          },
        ]}
        rows={roads}
      />
    </div>
  );
}
