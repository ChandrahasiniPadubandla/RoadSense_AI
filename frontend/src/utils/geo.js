// -----------------------------------------------------------------------
// Helpers for PostGIS GEOGRAPHY(POINT, 4326) columns coming back from the
// backend (roads.start_location, accidents.location, traffic_zones.location,
// accident_hotspots.location, ...).
//
// A GEOGRAPHY(POINT) column is NOT plain JSON — Postgres/PostGIS needs to be
// told how to serialize it. Ask your backend team which of these it returns,
// then keep ONLY the matching branch below (or all three, since this helper
// auto-detects the shape):
//
//   1. GeoJSON, via ST_AsGeoJSON(location)::json in the query:
//      { "type": "Point", "coordinates": [78.4867, 17.3850] }   // [lng, lat]
//
//   2. WKT/hex string, if the column is selected with no cast:
//      "0101000020E6100000..." — do NOT try to parse this in the frontend,
//      ask the backend to cast with ST_AsGeoJSON or ST_X/ST_Y instead.
//
//   3. Plain columns, if the backend already extracts lat/lng itself:
//      { "lat": 17.3850, "lng": 78.4867 }  or  { "latitude": ..., "longitude": ... }
// -----------------------------------------------------------------------

export function parseGeoPoint(value) {
  if (!value) return null;

  // Shape 3: already-flat lat/lng
  if (typeof value.lat === 'number' && typeof value.lng === 'number') {
    return { lat: value.lat, lng: value.lng };
  }
  if (typeof value.latitude === 'number' && typeof value.longitude === 'number') {
    return { lat: value.latitude, lng: value.longitude };
  }

  // Shape 1: GeoJSON Point -> coordinates are [lng, lat], note the order
  if (value.type === 'Point' && Array.isArray(value.coordinates)) {
    const [lng, lat] = value.coordinates;
    return { lat, lng };
  }

  // Shape 2: raw WKB/WKT hex string — can't safely parse client-side.
  if (typeof value === 'string') {
    console.warn(
      'Received a raw PostGIS string instead of GeoJSON. Ask the backend to ' +
        'wrap geography columns in ST_AsGeoJSON(...)::json.'
    );
    return null;
  }

  return null;
}

/** Build a GeoJSON Point payload to send back to the backend on create/update. */
export function toGeoPoint(lat, lng) {
  return { type: 'Point', coordinates: [lng, lat] };
}
