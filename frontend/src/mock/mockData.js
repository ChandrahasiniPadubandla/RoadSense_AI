// -----------------------------------------------------------------------
// This mock data intentionally mirrors the RAW shape your Postgres backend
// will send — same table names, same snake_case columns, geography points
// as GeoJSON. The api/*.js service files map this into the camelCase shape
// the React components use, so when the real backend replaces this mock,
// only the service files need to change, never the components.
// -----------------------------------------------------------------------

export const mockRoles = [
  { role_id: 1, role_name: 'SUPER_ADMIN', description: 'Full system access' },
  { role_id: 2, role_name: 'TRAFFIC_AUTHORITY', description: 'Traffic monitoring & predictions' },
  { role_id: 3, role_name: 'EMERGENCY_RESPONSE', description: 'Accident response tracking' },
  { role_id: 4, role_name: 'VIEWER', description: 'Read-only access' },
];

export const mockUsers = [
  { user_id: 1, role_id: 1, name: 'Ananya Rao', email: 'admin@traffic.gov', phone: '+91 90000 00001', is_active: true, password: 'admin123' },
  { user_id: 2, role_id: 2, name: 'Vikram Shah', email: 'authority@traffic.gov', phone: '+91 90000 00002', is_active: true, password: 'authority123' },
  { user_id: 3, role_id: 3, name: 'Meera Iyer', email: 'response@traffic.gov', phone: '+91 90000 00003', is_active: true, password: 'response123' },
  { user_id: 4, role_id: 4, name: 'Guest Viewer', email: 'viewer@traffic.gov', phone: null, is_active: true, password: 'viewer123' },
];

export const mockZones = [
  { zone_id: 1, zone_name: 'Central Business District', description: 'High-density commercial core', location: { type: 'Point', coordinates: [78.4744, 17.3753] } },
  { zone_id: 2, zone_name: 'Gachibowli IT Corridor', description: 'Tech park cluster', location: { type: 'Point', coordinates: [78.3489, 17.4401] } },
];

export const mockRoads = [
  { road_id: 101, zone_id: 1, road_name: 'NH-44', road_type: 'Highway', start_location: { type: 'Point', coordinates: [78.4867, 17.3850] }, end_location: { type: 'Point', coordinates: [78.4920, 17.3910] }, road_capacity: 200, speed_limit: 80, road_condition: 'Dry', number_of_lanes: 4, is_active: true },
  { road_id: 102, zone_id: 2, road_name: 'Outer Ring Road - Gachibowli', road_type: 'Ring Road', start_location: { type: 'Point', coordinates: [78.3489, 17.4401] }, end_location: { type: 'Point', coordinates: [78.3550, 17.4460] }, road_capacity: 260, speed_limit: 100, road_condition: 'Dry', number_of_lanes: 6, is_active: true },
  { road_id: 103, zone_id: 1, road_name: 'PV Narasimha Rao Expressway', road_type: 'Expressway', start_location: { type: 'Point', coordinates: [78.4744, 17.3753] }, end_location: { type: 'Point', coordinates: [78.4800, 17.3800] }, road_capacity: 300, speed_limit: 90, road_condition: 'Wet', number_of_lanes: 6, is_active: true },
  { road_id: 104, zone_id: 2, road_name: 'Jubilee Hills Road No. 36', road_type: 'Arterial', start_location: { type: 'Point', coordinates: [78.4071, 17.4326] }, end_location: { type: 'Point', coordinates: [78.4100, 17.4360] }, road_capacity: 120, speed_limit: 50, road_condition: 'Dry', number_of_lanes: 2, is_active: true },
  { road_id: 105, zone_id: 1, road_name: 'Begumpet Road', road_type: 'Arterial', start_location: { type: 'Point', coordinates: [78.4665, 17.4436] }, end_location: { type: 'Point', coordinates: [78.4700, 17.4470] }, road_capacity: 150, speed_limit: 50, road_condition: 'Dry', number_of_lanes: 3, is_active: true },
];

// Most recent traffic_records row per road (what a GET /traffic/roads/current
// endpoint would typically join and return alongside the road)
export const mockLatestTrafficByRoad = {
  101: { traffic_id: 9001, road_id: 101, timestamp: '2026-09-03T10:30:00Z', vehicle_count: 145, average_speed: 18, traffic_density: 0.72, congestion_level: 'HIGH', road_condition: 'Dry', weather_condition: 'Clear', rainfall: 0, temperature: 32, visibility: 10, is_holiday: false },
  102: { traffic_id: 9002, road_id: 102, timestamp: '2026-09-03T10:30:00Z', vehicle_count: 90, average_speed: 46, traffic_density: 0.35, congestion_level: 'LOW', road_condition: 'Dry', weather_condition: 'Clear', rainfall: 0, temperature: 31, visibility: 10, is_holiday: false },
  103: { traffic_id: 9003, road_id: 103, timestamp: '2026-09-03T10:29:00Z', vehicle_count: 260, average_speed: 12, traffic_density: 0.87, congestion_level: 'SEVERE', road_condition: 'Wet', weather_condition: 'Rain', rainfall: 12.4, temperature: 26, visibility: 4, is_holiday: false },
  104: { traffic_id: 9004, road_id: 104, timestamp: '2026-09-03T10:28:00Z', vehicle_count: 60, average_speed: 30, traffic_density: 0.50, congestion_level: 'MEDIUM', road_condition: 'Dry', weather_condition: 'Cloudy', rainfall: 0, temperature: 29, visibility: 9, is_holiday: false },
  105: { traffic_id: 9005, road_id: 105, timestamp: '2026-09-03T10:27:00Z', vehicle_count: 132, average_speed: 15, traffic_density: 0.88, congestion_level: 'HIGH', road_condition: 'Dry', weather_condition: 'Clear', rainfall: 0, temperature: 32, visibility: 10, is_holiday: false },
};

export const mockTrafficPredictions = [
  { prediction_id: 5001, road_id: 101, prediction_time: '2026-09-03T10:30:00Z', target_time: '2026-09-03T18:00:00Z', predicted_congestion: 'HIGH', predicted_vehicle_count: 210, confidence_score: 0.86, model_version_id: 1 },
  { prediction_id: 5002, road_id: 103, prediction_time: '2026-09-03T10:30:00Z', target_time: '2026-09-03T17:30:00Z', predicted_congestion: 'SEVERE', predicted_vehicle_count: 310, confidence_score: 0.91, model_version_id: 1 },
  { prediction_id: 5003, road_id: 105, prediction_time: '2026-09-03T10:30:00Z', target_time: '2026-09-03T18:00:00Z', predicted_congestion: 'MEDIUM', predicted_vehicle_count: 150, confidence_score: 0.72, model_version_id: 1 },
];

export const mockAccidents = [
  { accident_id: 2001, road_id: 101, location: { type: 'Point', coordinates: [78.489, 17.386] }, accident_datetime: '2026-08-29T19:12:00Z', weather_condition: 'Rain', road_condition: 'Wet', vehicle_count: 3, number_of_vehicles: 3, severity: 'SEVERE', fatalities: 0, injuries: 2, description: 'Rear-end collision during heavy rainfall.', created_by: 2 },
  { accident_id: 2002, road_id: 102, location: { type: 'Point', coordinates: [78.3475, 17.4405] }, accident_datetime: '2026-08-27T08:41:00Z', weather_condition: 'Clear', road_condition: 'Dry', vehicle_count: 2, number_of_vehicles: 2, severity: 'MODERATE', fatalities: 0, injuries: 1, description: 'Side collision at merge point.', created_by: 2 },
  { accident_id: 2003, road_id: 103, location: { type: 'Point', coordinates: [78.472, 17.376] }, accident_datetime: '2026-08-22T21:55:00Z', weather_condition: 'Fog', road_condition: 'Wet', vehicle_count: 4, number_of_vehicles: 4, severity: 'FATAL', fatalities: 1, injuries: 3, description: 'Multi-vehicle pile-up in low visibility.', created_by: 3 },
];

export const mockAccidentPredictions = [
  { prediction_id: 6001, road_id: 103, prediction_time: '2026-09-03T10:30:00Z', risk_percentage: 89, risk_level: 'HIGH', confidence_score: 0.88, model_version_id: 2 },
  { prediction_id: 6002, road_id: 101, prediction_time: '2026-09-03T10:30:00Z', risk_percentage: 61, risk_level: 'MEDIUM', confidence_score: 0.75, model_version_id: 2 },
];

export const mockHotspots = [
  { hotspot_id: 1, zone_id: 1, location: { type: 'Point', coordinates: [78.489, 17.386] }, accident_count: 43, risk_score: 0.91, risk_level: 'HIGH', calculated_at: '2026-09-01T00:00:00Z' },
  { hotspot_id: 2, zone_id: 2, location: { type: 'Point', coordinates: [78.3475, 17.4405] }, accident_count: 19, risk_score: 0.58, risk_level: 'MEDIUM', calculated_at: '2026-09-01T00:00:00Z' },
  { hotspot_id: 3, zone_id: 1, location: { type: 'Point', coordinates: [78.472, 17.376] }, accident_count: 27, risk_score: 0.83, risk_level: 'HIGH', calculated_at: '2026-09-01T00:00:00Z' },
];

export const mockAnomalies = [
  { anomaly_id: 1, road_id: 103, traffic_id: 9003, detected_at: '2026-09-03T09:15:00Z', normal_vehicle_count: 500, actual_vehicle_count: 1400, anomaly_score: 2.8, anomaly_type: 'VOLUME_SPIKE', description: 'Traffic volume 2.8x above normal baseline.', status: 'ACTIVE' },
];

export const mockAlerts = [
  { alert_id: 1, road_id: 103, prediction_id: 5002, alert_type: 'CONGESTION', severity: 'HIGH', message: 'Severe congestion predicted 17:30-19:00', created_at: '2026-09-03T09:00:00Z', status: 'ACTIVE', resolved_at: null },
  { alert_id: 2, road_id: 103, prediction_id: 6001, alert_type: 'ACCIDENT_RISK', severity: 'HIGH', message: 'Accident risk 89% due to heavy rainfall and high speed', created_at: '2026-09-03T09:05:00Z', status: 'ACTIVE', resolved_at: null },
  { alert_id: 3, road_id: 103, prediction_id: null, alert_type: 'ANOMALY', severity: 'MEDIUM', message: 'Traffic volume 2.8x above normal', created_at: '2026-09-03T09:15:00Z', status: 'RESOLVED', resolved_at: '2026-09-03T09:40:00Z' },
];

export const mockEmergencyResponses = [
  { response_id: 1, accident_id: 2001, assigned_user_id: 3, response_status: 'EN_ROUTE', assigned_at: '2026-08-29T19:15:00Z', arrived_at: null, resolved_at: null, notes: 'Ambulance dispatched from Zone 1 station.' },
  { response_id: 2, accident_id: 2003, assigned_user_id: 3, response_status: 'RESOLVED', assigned_at: '2026-08-22T21:58:00Z', arrived_at: '2026-08-22T22:10:00Z', resolved_at: '2026-08-22T23:05:00Z', notes: 'Scene cleared, one fatality confirmed on arrival.' },
];

export const mockTrafficHistory = [
  { hour: '06:00', vehicles: 210 }, { hour: '08:00', vehicles: 480 },
  { hour: '10:00', vehicles: 320 }, { hour: '12:00', vehicles: 300 },
  { hour: '14:00', vehicles: 340 }, { hour: '16:00', vehicles: 410 },
  { hour: '18:00', vehicles: 520 }, { hour: '20:00', vehicles: 260 },
];

export const mockDashboardStats = {
  activeRoads: 128,
  highTraffic: 24,
  accidentAlerts: 5,
  highRiskZones: 9,
};
