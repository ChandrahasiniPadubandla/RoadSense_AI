import React, { useState, useEffect } from "react";
import axios from "axios";

const AnomaliesPage = () => {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Form state for manual anomaly prediction
  const [formData, setFormData] = useState({
    road_id: "",
    vehicle_count: "",
    average_speed: "",
    traffic_density: "",
    road_capacity: "",
    previous_traffic: "",
    hour: ""
  });
  const [prediction, setPrediction] = useState(null);

  // Fetch anomalies from backend
  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        const res = await axios.get("/api/anomalies"); // calls list_traffic_anomalies
        setAnomalies(res.data);
      } catch (err) {
        setError("Error fetching anomalies");
      } finally {
        setLoading(false);
      }
    };
    fetchAnomalies();
  }, []);

  // Handle form input changes
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // Submit anomaly prediction request
  const handlePredict = async () => {
    try {
      const res = await axios.post("/api/anomalies/predict", formData);
      setPrediction(res.data);
    } catch (err) {
      setError("Error predicting anomaly");
    }
  };

  return (
    <div className="anomalies-page">
      <h2>Traffic Anomalies</h2>
      <p>Unusual traffic patterns detected by the ML model.</p>

      {loading && <p>Loading anomalies...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && anomalies.length === 0 && <p>No anomalies found.</p>}

      {anomalies.length > 0 && (
        <table border="1" style={{ width: "100%", marginTop: "10px" }}>
          <thead>
            <tr>
              <th>Road</th>
              <th>Detected At</th>
              <th>Type</th>
              <th>Score</th>
              <th>Normal Vehicle Count</th>
              <th>Actual Vehicle Count</th>
              <th>Description</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {anomalies.map((a) => (
              <tr key={a.anomaly_id}>
                <td>{a.road_name || "Unknown"}</td>
                <td>{a.detected_at}</td>
                <td>{a.anomaly_type}</td>
                <td>{a.anomaly_score}</td>
                <td>{a.normal_vehicle_count}</td>
                <td>{a.actual_vehicle_count}</td>
                <td>{a.description}</td>
                <td>{a.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3 style={{ marginTop: "20px" }}>Test Anomaly Prediction</h3>
      <form>
        <label>Road ID:</label>
        <input name="road_id" value={formData.road_id} onChange={handleChange} />

        <label>Vehicle Count:</label>
        <input name="vehicle_count" value={formData.vehicle_count} onChange={handleChange} />

        <label>Average Speed:</label>
        <input name="average_speed" value={formData.average_speed} onChange={handleChange} />

        <label>Traffic Density:</label>
        <input name="traffic_density" value={formData.traffic_density} onChange={handleChange} />

        <label>Road Capacity:</label>
        <input name="road_capacity" value={formData.road_capacity} onChange={handleChange} />

        <label>Previous Traffic:</label>
        <input name="previous_traffic" value={formData.previous_traffic} onChange={handleChange} />

        <label>Hour:</label>
        <input name="hour" value={formData.hour} onChange={handleChange} />

        <button type="button" onClick={handlePredict}>Predict Anomaly</button>
      </form>

      {prediction && (
        <div className="prediction-results" style={{ marginTop: "15px" }}>
          <h4>Prediction Result</h4>
          <p>Anomaly Type: {prediction.anomaly_type}</p>
          <p>Anomaly Score: {prediction.anomaly_score}</p>
          <p>Description: {prediction.description}</p>
          <p>Status: {prediction.status}</p>
        </div>
      )}
    </div>
  );
};

export default AnomaliesPage;
