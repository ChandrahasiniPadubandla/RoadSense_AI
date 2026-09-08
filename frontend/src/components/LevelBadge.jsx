import React from 'react';

/**
 * Generic pill badge. Pass a colorMap (see utils/constants.js) plus the level key.
 * Example: <LevelBadge level={road.trafficLevel} colorMap={TRAFFIC_LEVEL_COLOR} />
 */
export default function LevelBadge({ level, colorMap }) {
  const classes = colorMap[level] || 'text-asphalt-300 border-asphalt-600 bg-asphalt-800';
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${classes}`}
    >
      {level}
    </span>
  );
}
