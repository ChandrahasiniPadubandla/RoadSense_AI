import React, { useEffect, useState } from 'react';
import LevelBadge from '../components/LevelBadge';
import { RISK_LEVEL_COLOR } from '../utils/constants';
import * as accidentService from '../api/accidentService';

export default function AccidentRiskPrediction() {
  const [predictions, setPredictions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    accidentService.getRiskPredictions().then((data) => {
      setPredictions(data);
      setIsLoading(false);
    });
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Scoring accident risk…</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-asphalt-400">
        Risk score combines traffic density, speed, weather, and historical accident counts.
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {predictions.map((p) => (
          <div
            key={p.roadId}
            className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-5"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-asphalt-100">{p.roadName}</p>
                <p className="mt-1 text-xs text-asphalt-400">Segment {p.roadId}</p>
              </div>
              <LevelBadge level={p.riskLevel} colorMap={RISK_LEVEL_COLOR} />
            </div>

            <p className="data-num mt-4 text-4xl font-semibold text-asphalt-100">
              {p.riskPercent}%
            </p>
            <p className="text-xs text-asphalt-400">predicted accident risk</p>

            <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <Factor label="Traffic density" value={p.factors.trafficDensity} />
              <Factor label="Avg speed" value={`${p.factors.avgSpeed} km/h`} />
              <Factor label="Rainfall" value={p.factors.rainfall} />
              <Factor label="Historical accidents" value={p.factors.historicalAccidents} />
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}

function Factor({ label, value }) {
  return (
    <div className="rounded-md border border-asphalt-800 bg-asphalt-950/60 px-3 py-2">
      <dt className="text-asphalt-400">{label}</dt>
      <dd className="mt-0.5 text-asphalt-100">{value}</dd>
    </div>
  );
}
