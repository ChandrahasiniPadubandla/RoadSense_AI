import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, "traffic_congestion")
import traffic_anomaly

scenarios = {
    "Condition 1: Severe Weather / Monsoon Flash Flood": {
        "vehicle_count": 1100.0,
        "average_speed": 10.0,
        "speed_limit": 50.0,
        "road_capacity": 2400.0,
        "slowdown_percentage": 80.0,
        "delay_seconds": 720.0,
        "free_flow_seconds": 60.0,
        "road_closure": False,
        "rainfall": 65.0,
        "hour": 18.0,
        "notes": "Flooded underpass / cloudburst; extreme rain with speed collapse."
    },
    "Condition 2: Multi-Vehicle Crash / Sudden Corridor Breakdown": {
        "vehicle_count": 1600.0,
        "average_speed": 6.0,
        "speed_limit": 80.0,
        "road_capacity": 4000.0,
        "slowdown_percentage": 92.5,
        "delay_seconds": 1200.0,
        "free_flow_seconds": 60.0,
        "road_closure": False,
        "rainfall": 0.0,
        "hour": 17.0,
        "notes": "Catastrophic 92% speed drop on an 80 km/h expressway (Outer Ring Road)."
    },
    "Condition 3: Off-Peak Midnight Gridlock (Temporal Anomaly)": {
        "vehicle_count": 950.0,
        "average_speed": 12.0,
        "speed_limit": 50.0,
        "road_capacity": 2200.0,
        "slowdown_percentage": 76.0,
        "delay_seconds": 480.0,
        "free_flow_seconds": 60.0,
        "road_closure": False,
        "rainfall": 0.0,
        "hour": 2.0,
        "notes": "Severe jam occurring at 2:00 AM when flow should be free."
    },
    "Condition 4: Extreme Over-Capacity Bottleneck (Festival / Massive Surge)": {
        "vehicle_count": 3200.0,
        "average_speed": 8.0,
        "speed_limit": 40.0,
        "road_capacity": 2000.0,
        "slowdown_percentage": 80.0,
        "delay_seconds": 900.0,
        "free_flow_seconds": 60.0,
        "road_closure": False,
        "rainfall": 0.0,
        "hour": 20.0,
        "notes": "160% capacity saturation (3200 vehicles on a 2000-capacity road)."
    },
    "Condition 5: Expected Peak Rush Hour (Normal Baseline)": {
        "vehicle_count": 1400.0,
        "average_speed": 28.0,
        "speed_limit": 50.0,
        "road_capacity": 2400.0,
        "slowdown_percentage": 44.0,
        "delay_seconds": 120.0,
        "free_flow_seconds": 60.0,
        "road_closure": False,
        "rainfall": 0.0,
        "hour": 18.5,
        "notes": "Typical evening rush: moderate speed drop, within normal historical limits."
    }
}

for title, data in scenarios.items():
    res = traffic_anomaly.predict_anomaly(data)
    feat = traffic_anomaly._prepare_feature_row(data)
    df_in = pd.DataFrame([feat])[traffic_anomaly.features]
    scaled = traffic_anomaly.scaler.transform(df_in)[0]
    
    print("======================================================================")
    print(f"SCENARIO: {title}")
    print(f"Notes: {data['notes']}")
    print(f"PREDICTION: {res['status']} | Decision Score: {res['anomaly_score']} | Conf: {res['confidence_score']}%")
    print("----------------------------------------------------------------------")
    print("Key Feature Values & Z-Scores:")
    for col, z in zip(traffic_anomaly.features, scaled):
        val = feat[col]
        flag = " [OUTLIER]" if abs(z) > 2.5 else ""
        print(f"  {col:22}: raw = {val:7.2f} | Z-score = {z:+6.2f} sigma{flag}")
print("======================================================================")
