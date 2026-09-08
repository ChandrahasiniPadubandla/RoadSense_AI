import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import LevelBadge from '../components/LevelBadge';
import { TRAFFIC_LEVEL_COLOR } from '../utils/constants';
import * as trafficService from '../api/trafficService';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [roads, setRoads] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      const [statsRes, historyRes, roadsRes] = await Promise.all([
        trafficService.getDashboardStats(),
        trafficService.getTrafficHistory(),
        trafficService.getRoads(),
      ]);
      if (!isMounted) return;
      setStats(statsRes);
      setHistory(historyRes);
      setRoads(roadsRes);
      setIsLoading(false);
    }
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return <p className="text-sm text-asphalt-400">Loading dashboard…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Active Roads" value={stats.activeRoads} />
        <StatCard label="High Traffic" value={stats.highTraffic} accent="text-signal-amber" />
        <StatCard label="Accident Alerts" value={stats.accidentAlerts} accent="text-signal-red" />
        <StatCard label="High Risk Zones" value={stats.highRiskZones} accent="text-signal-red" />
      </div>

      <div className="rounded-lg border border-asphalt-700 bg-asphalt-900 p-5">
        <p className="mb-4 text-sm font-medium text-asphalt-100">
          Vehicle volume — last 24h (sampled)
        </p>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid stroke="#282D34" vertical={false} />
              <XAxis dataKey="hour" stroke="#7A828C" fontSize={12} />
              <YAxis stroke="#7A828C" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: '#1D2126',
                  border: '1px solid #282D34',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="vehicles"
                stroke="#3E7CB1"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="mb-3 text-sm font-medium text-asphalt-100">Road status</p>
        <DataTable
          columns={[
            { key: 'name', header: 'Road' },
            { key: 'vehicleCount', header: 'Vehicles' },
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
    </div>
  );
}
