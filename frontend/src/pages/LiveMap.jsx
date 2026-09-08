import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import * as trafficService from '../api/trafficService';
import * as accidentService from '../api/accidentService';

const LEVEL_COLOR = {
  LOW: '#3FA772',
  MEDIUM: '#E8A33D',
  HIGH: '#D14343',
  SEVERE: '#D14343',
};

export default function LiveMap() {
  const [roads, setRoads] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([trafficService.getRoads(), accidentService.getHotspots()]).then(
      ([roadsRes, hotspotsRes]) => {
        setRoads(roadsRes);
        setHotspots(hotspotsRes);
        setIsLoading(false);
      }
    );
  }, []);

  if (isLoading) return <p className="text-sm text-asphalt-400">Loading map…</p>;

  const center = roads.length ? [roads[0].lat, roads[0].lng] : [17.385, 78.4867];

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4 text-xs text-asphalt-300">
        <Legend color="#3FA772" label="Low traffic" />
        <Legend color="#E8A33D" label="Moderate traffic" />
        <Legend color="#D14343" label="Heavy traffic" />
        <Legend color="#D14343" label="Accident hotspot" ring />
      </div>

      <div className="flex-1 overflow-hidden rounded-lg border border-asphalt-700">
        <MapContainer center={center} zoom={12} className="h-full w-full">
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {roads.map((road) => (
            <CircleMarker
              key={road.id}
              center={[road.lat, road.lng]}
              radius={9}
              pathOptions={{
                color: LEVEL_COLOR[road.trafficLevel],
                fillColor: LEVEL_COLOR[road.trafficLevel],
                fillOpacity: 0.7,
              }}
            >
              <Popup>
                <strong>{road.name}</strong>
                <br />
                {road.vehicleCount} vehicles · {road.avgSpeed} km/h
                <br />
                Level: {road.trafficLevel}
              </Popup>
            </CircleMarker>
          ))}

          {hotspots.map((hotspot) => (
            <CircleMarker
              key={hotspot.id}
              center={[hotspot.lat, hotspot.lng]}
              radius={14}
              pathOptions={{
                color: '#D14343',
                fillColor: 'transparent',
                weight: 2,
              }}
            >
              <Popup>
                <strong>{hotspot.location}</strong>
                <br />
                {hotspot.accidentCount} accidents recorded
                <br />
                Risk: {hotspot.riskLevel}
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}

function Legend({ color, label, ring }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block h-2.5 w-2.5 rounded-full"
        style={
          ring
            ? { border: `2px solid ${color}`, background: 'transparent' }
            : { background: color }
        }
      />
      {label}
    </div>
  );
}
