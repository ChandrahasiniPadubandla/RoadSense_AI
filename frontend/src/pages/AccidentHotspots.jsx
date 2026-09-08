import React, { useEffect, useState } from 'react';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { RISK_LEVEL_COLOR } from '../utils/constants';
import * as accidentService from '../api/accidentService';

export default function AccidentHotspots() {
  const [hotspots, setHotspots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    accidentService.getHotspots().then((data) => {
      setHotspots(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Identifying hotspots…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        Locations with the highest frequency of recorded accidents.
      </p>
      <DataTable
        columns={[
          { key: 'location', header: 'Location' },
          { key: 'accidentCount', header: 'Accidents recorded' },
          {
            key: 'riskLevel',
            header: 'Risk',
            render: (row) => (
              <LevelBadge level={row.riskLevel} colorMap={RISK_LEVEL_COLOR} />
            ),
          },
        ]}
        rows={hotspots}
      />
    </div>
  );
}
