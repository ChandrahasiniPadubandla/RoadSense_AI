import urllib.request
import json
import sys
from pathlib import Path

backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from app.security import create_access_token
from app.database.connection import SessionLocal
from app.database.models import User

db = SessionLocal()
user = db.query(User).filter(User.email == "padubandlachandrahasini.anasol@gmail.com").first()
token = create_access_token(user.user_id)
db.close()

base_url = "http://127.0.0.1:8000"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

test_routes = [
    {
        "case": "Case 1: Road Closed / Heavy Incident Corridor",
        "start": "KBR Park Nature Trail, Banjara Hills, Hyderabad",
        "end": "HITEC City–Kondapur Main Road, Madhapur, Hyderabad"
    },
    {
        "case": "Case 2: High-Speed Arterial / Normal Flow (Financial District / Gachibowli)",
        "start": "Gachibowli Main Road, Hyderabad",
        "end": "Financial District Road, Hyderabad"
    },
    {
        "case": "Case 3: Urban Transit Corridor (Kukatpally to JNTU)",
        "start": "Kukatpally Main Road, Hyderabad",
        "end": "JNTU Road, Hyderabad"
    },
    {
        "case": "Case 4: Dense Core Corridor (Charminar to Nampally)",
        "start": "Charminar Road, Hyderabad",
        "end": "Nampally Road, Hyderabad"
    },
    {
        "case": "Case 5: East-West Arterial (Uppal to Secunderabad/Paradise)",
        "start": "Uppal Main Road, Hyderabad",
        "end": "Paradise Main Road, Hyderabad"
    }
]

print("================================================================================")
print("TESTING HYDERABAD CORRIDORS ACROSS ALL ANOMALY CASES")
print("================================================================================")

for t in test_routes:
    payload = {
        "start_location": t["start"],
        "end_location": t["end"]
    }
    req = urllib.request.Request(
        f"{base_url}/predictions/traffic/route",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            live = data.get("live_traffic") or {}
            anom = data.get("anomaly_detection") or {}
            
            print(f"\n--- {t['case']} ---")
            print(f"Route: {t['start']} -> {t['end']}")
            print(f"Matched Road: {data.get('road_name')}")
            print(f"Congestion: {data.get('congestion_level')} | Est Time: {data.get('estimated_time')}")
            print(f"Live Flow: Condition='{live.get('traffic_condition')}' | Closure={live.get('road_closure')} | Speed={live.get('current_speed_kmh')}/{live.get('free_flow_speed_kmh')} km/h | Slowdown={live.get('slowdown_percentage')}% | Delay={live.get('delay_minutes')}m")
            print(f"ML Anomaly Model: Status={anom.get('prediction')} | is_anomaly={anom.get('is_anomaly')} | Score={anom.get('anomaly_score')} | Conf={anom.get('confidence_score')}%")
    except Exception as e:
        print(f"Error testing {t['case']}: {e}")
