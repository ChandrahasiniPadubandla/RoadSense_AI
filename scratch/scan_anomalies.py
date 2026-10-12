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

candidates = [
    ("KBR Park Nature Trail, Banjara Hills, Hyderabad", "HITEC City–Kondapur Main Road, Madhapur, Hyderabad"),
    ("Banjara Hills Road No 1, Hyderabad", "Jubilee Hills Check Post, Hyderabad"),
    ("Punjagutta Flyover, Hyderabad", "Ameerpet Metro Station, Hyderabad"),
    ("Begumpet Flyover, Hyderabad", "Secunderabad Railway Station, Hyderabad"),
    ("Tolichowki Flyover, Hyderabad", "Mehdipatnam Bus Stand, Hyderabad"),
    ("Dilsukhnagar Bus Depot, Hyderabad", "LB Nagar Ring Road, Hyderabad"),
    ("Cyber Towers, Hitec City, Hyderabad", "Mindspace Junction, Madhapur, Hyderabad"),
    ("IKEA, Madhapur, Hyderabad", "Biodiversity Junction, Gachibowli, Hyderabad"),
    ("Nanakramguda Circle, Hyderabad", "Wipro Circle, Financial District, Hyderabad"),
    ("Moosapet Metro Station, Hyderabad", "Bharat Nagar Flyover, Hyderabad"),
    ("Ranigunj, Secunderabad, Hyderabad", "MG Road, Secunderabad, Hyderabad"),
    ("Masab Tank, Hyderabad", "NMDC, Mehdipatnam, Hyderabad"),
    ("Kothaguda Junction, Kondapur, Hyderabad", "Botanical Garden, Gachibowli, Hyderabad"),
    ("Paradise Circle, Secunderabad, Hyderabad", "Bowenpally Check Post, Hyderabad"),
    ("Miyapur Metro Station, Hyderabad", "Kukatpally Housing Board Colony, Hyderabad"),
    ("Malakpet Metro Station, Hyderabad", "Dilsukhnagar, Hyderabad"),
    ("Mehdipatnam Main Road, Hyderabad", "Attapur Pillar 140, Hyderabad"),
]

base_url = "http://127.0.0.1:8000"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

print("=== SCANNING CANDIDATE ROUTES FOR ANOMALIES ===")
sys.stdout.flush()

anomaly_found = []
normal_found = []

for start, end in candidates:
    payload = {"start_location": start, "end_location": end}
    req = urllib.request.Request(
        f"{base_url}/predictions/traffic/route",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            anom = data.get("anomaly_detection") or {}
            live = data.get("live_traffic") or {}
            is_anom = anom.get("is_anomaly")
            score = anom.get("anomaly_score")
            road = data.get("road_name")
            status = anom.get("prediction")
            short_s = start.split(",")[0]
            short_e = end.split(",")[0]
            print(f"[{status}] {short_s} -> {short_e} | Score: {score} | Closed: {live.get('road_closure')} | Slowdown: {live.get('slowdown_percentage')}% | Delay: {live.get('delay_minutes')}m")
            sys.stdout.flush()
            if is_anom:
                anomaly_found.append({
                    "start": start,
                    "end": end,
                    "road": road,
                    "score": score,
                    "conf": anom.get("confidence_score"),
                    "live": live
                })
            else:
                normal_found.append({
                    "start": start,
                    "end": end,
                    "road": road,
                    "score": score
                })
    except Exception as e:
        print(f"Err {start.split(',')[0]}: {e}")
        sys.stdout.flush()

print(f"\n==========================================")
print(f"TOTAL ANOMALIES IDENTIFIED: {len(anomaly_found)}")
print(f"==========================================")
for a in anomaly_found:
    print(f"\n>>> ANOMALY ROUTE:")
    print(f"  Start: '{a['start']}'")
    print(f"  End:   '{a['end']}'")
    print(f"  Road:  {a['road']}")
    print(f"  Score: {a['score']} (Confidence: {a['conf']}%)")
    print(f"  Live:  Condition={a['live'].get('traffic_condition')}, Closed={a['live'].get('road_closure')}, Slowdown={a['live'].get('slowdown_percentage')}%, Delay={a['live'].get('delay_minutes')}m")

