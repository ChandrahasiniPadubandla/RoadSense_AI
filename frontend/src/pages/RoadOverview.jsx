import React, { useEffect, useState } from 'react';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR, RISK_LEVEL_COLOR } from '../utils/constants';
import * as trafficService from '../api/trafficService';
import * as accidentService from '../api/accidentService';

/**
 * "Merge them some sort" — this page puts each road's current traffic
 * level and predicted accident risk side by side, so an authority can see
 * both signals for a road in one glance instead of switching between the
 * Traffic Monitoring and Accident Risk Prediction pages.
 */
export default function RoadOverview() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([trafficService.getRoads(), accidentService.getRiskPredictions()]).then(
      ([roads, riskPredictions]) => {
        const riskByRoadId = Object.fromEntries(riskPredictions.map((r) => [r.roadId, r]));
        const merged = roads.map((road) => ({
          ...road,
          risk: riskByRoadId[road.id] || null,
        }));
        // Highest combined concern first: SEVERE/HIGH traffic + HIGH risk roads surface first.
        merged.sort((a, b) => (b.risk?.riskPercent || 0) - (a.risk?.riskPercent || 0));
        setRows(merged);
        setIsLoading(false);
      }
    );
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading combined overview…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        Live congestion and predicted accident risk together, per road — highest concern first.
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {rows.map((road) => (
          <div
            key={road.id}
            className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-4"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-asphalt-100">{road.name}</p>
                <p className="mt-0.5 text-xs text-asphalt-400">{road.roadType}</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-md border border-asphalt-800 bg-asphalt-950/60 px-3 py-2">
                <p className="text-xs text-asphalt-400">Traffic</p>
                <p className="data-num mt-1 text-lg font-semibold text-asphalt-100">
                  {road.vehicleCount ?? '—'}
                </p>
                <p className="mb-1 text-xs text-asphalt-400">vehicles</p>
                <LevelBadge level={road.trafficLevel} colorMap={TRAFFIC_LEVEL_COLOR} />
              </div>

              <div className="rounded-md border border-asphalt-800 bg-asphalt-950/60 px-3 py-2">
                <p className="text-xs text-asphalt-400">Accident risk</p>
                <p className="data-num mt-1 text-lg font-semibold text-asphalt-100">
                  {road.risk ? `${road.risk.riskPercent}%` : '—'}
                </p>
                <p className="mb-1 text-xs text-asphalt-400">predicted</p>
                {road.risk ? (
                  <LevelBadge level={road.risk.riskLevel} colorMap={RISK_LEVEL_COLOR} />
                ) : (
                  <span className="text-xs text-asphalt-500">No prediction yet</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
