import json
import logging
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint
from geoalchemy2.shape import to_shape

from app.database.models import Road

logger = logging.getLogger("roadsense.geocoding")

# Simple in-memory cache to avoid redundant external network calls
_GEOCODE_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_REVERSE_CACHE: Dict[str, Dict[str, Any]] = {}
USER_AGENT = "RoadSenseAI-Backend/1.0 (contact@roadsense.ai)"


def geocode_location(query: str, city_bias: str = "Hyderabad", limit: int = 5) -> List[Dict[str, Any]]:
    """
    Geocodes an address or landmark name into real latitude and longitude.
    Uses OpenStreetMap Nominatim with local in-memory caching.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    cache_key = f"{clean_query.lower()}_{city_bias.lower()}_{limit}"
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    # Append city bias if not already present in search term
    search_term = clean_query
    if city_bias and city_bias.lower() not in clean_query.lower():
        search_term = f"{clean_query}, {city_bias}"

    params = {
        "q": search_term,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "countrycodes": "in"
    }
    url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in data:
            results.append({
                "display_name": item.get("display_name", ""),
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "type": item.get("type", "location"),
                "importance": float(item.get("importance", 0.0)),
                "address": item.get("address", {})
            })

        _GEOCODE_CACHE[cache_key] = results
        return results
    except Exception as err:
        logger.warning("Geocoding failed for '%s': %s", clean_query, err)
        return []


def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Reverse-geocodes exact GPS coordinates into a human-readable street/area name.
    """
    cache_key = f"{round(latitude, 4)}_{round(longitude, 4)}"
    if cache_key in _REVERSE_CACHE:
        return _REVERSE_CACHE[cache_key]

    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1
    }
    url = f"https://nominatim.openstreetmap.org/reverse?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        addr = data.get("address", {})
        road_name = (
            addr.get("road")
            or addr.get("suburb")
            or addr.get("neighbourhood")
            or addr.get("residential")
            or addr.get("city")
            or "Selected Location"
        )

        result = {
            "display_name": data.get("display_name", f"Location ({latitude:.4f}, {longitude:.4f})"),
            "road": road_name,
            "suburb": addr.get("suburb"),
            "neighbourhood": addr.get("neighbourhood"),
            "city": addr.get("city") or addr.get("state_district"),
            "state": addr.get("state"),
            "postcode": addr.get("postcode"),
            "latitude": latitude,
            "longitude": longitude
        }

        _REVERSE_CACHE[cache_key] = result
        return result
    except Exception as err:
        logger.warning("Reverse geocoding failed for (%s, %s): %s", latitude, longitude, err)
        return None


def find_nearest_road_by_coordinates(db: Session, latitude: float, longitude: float, max_distance_meters: float = 3000.0) -> Optional[Road]:
    """
    Uses PostGIS spatial indexing to find the closest road segment to given coordinates within max_distance_meters.
    Returns None if no road is within the threshold.
    """
    try:
        from geoalchemy2 import func
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        road = (
            db.query(Road)
            .filter(Road.route_geometry.isnot(None))
            .filter(func.ST_DWithin(func.geography(Road.route_geometry), func.geography(point), max_distance_meters))
            .order_by(func.ST_Distance(func.geography(Road.route_geometry), func.geography(point)))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS route_geometry distance query failed: %s", err)

    try:
        from geoalchemy2 import func
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        road = (
            db.query(Road)
            .filter(Road.start_location.isnot(None))
            .filter(func.ST_DWithin(func.geography(Road.start_location), func.geography(point), max_distance_meters))
            .order_by(func.ST_Distance(func.geography(Road.start_location), func.geography(point)))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS start_location distance query failed: %s", err)

    return None



# In-memory driving route cache: "(round(lat1, 4), round(lng1, 4), round(lat2, 4), round(lng2, 4))" -> route dict
_ROUTE_CACHE: Dict[str, Dict[str, Any]] = {}


def get_driving_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float
) -> Dict[str, Any]:
    """
    Fetches the real-world street driving route geometry between start and destination coordinates.
    Uses Open Source Routing Machine (OSRM) to trace actual turns, curved roads, and highways.
    Returns:
      {
        "coordinates": [[lat, lng], [lat, lng], ...],
        "distance_km": float,
        "duration_minutes": float,
        "is_real_route": bool
      }
    """
    cache_key = f"{round(start_lat, 4)}_{round(start_lng, 4)}_{round(end_lat, 4)}_{round(end_lng, 4)}"
    if cache_key in _ROUTE_CACHE:
        return _ROUTE_CACHE[cache_key]

    # Call OSRM public routing API (OSRM expects lng,lat format)
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("code") == "Ok" and data.get("routes"):
            primary_route = data["routes"][0]
            # OSRM geometry is GeoJSON coordinates: [[lng, lat], ...]
            # Leaflet Polyline expects: [[lat, lng], ...]
            raw_coords = primary_route["geometry"]["coordinates"]
            leaflet_coords = [[round(pt[1], 6), round(pt[0], 6)] for pt in raw_coords]
            dist_km = round(primary_route["distance"] / 1000.0, 2)
            dur_mins = round(primary_route["duration"] / 60.0, 1)

            res = {
                "coordinates": leaflet_coords,
                "distance_km": dist_km,
                "duration_minutes": dur_mins,
                "is_real_route": True
            }
            _ROUTE_CACHE[cache_key] = res
            return res
    except Exception as err:
        logger.warning("OSRM driving route request failed (%s): %s", url, err)

    # Fallback to straight line if external routing fails
    import math
    dlat = math.radians(end_lat - start_lat)
    dlon = math.radians(end_lng - start_lng)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(start_lat))
        * math.cos(math.radians(end_lat))
        * math.sin(dlon / 2) ** 2
    )
    dist_km = round(6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

    fallback_res = {
        "coordinates": [[round(start_lat, 6), round(start_lng, 6)], [round(end_lat, 6), round(end_lng, 6)]],
        "distance_km": dist_km,
        "duration_minutes": round(dist_km * 2.5, 1),
        "is_real_route": False
    }
    return fallback_res


def get_accidents_along_route(
    db: Session,
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    road_id: Optional[Any] = None,
    risk_percentage: float = 0.0,
    risk_level: str = "LOW",
    route_coords: Optional[List[List[float]]] = None
) -> List[Dict[str, Any]]:
    """
    Identifies and returns all accident points along the route corridor:
    1. Historical accident records from database along this road or in route proximity.
    2. Primary predicted accident hazard hotspot point along the route geometry.
    """
    from app.database.models import Accident
    points: List[Dict[str, Any]] = []

    # 1. Query historical accidents from DB for this road
    if road_id:
        accidents = db.query(Accident).filter(Accident.road_id == road_id).limit(6).all()
        for acc in accidents:
            if acc.location is not None:
                try:
                    pt = to_shape(acc.location)
                    points.append({
                        "id": str(acc.accident_id),
                        "latitude": round(pt.y, 6),
                        "longitude": round(pt.x, 6),
                        "type": "historical",
                        "severity": acc.severity or "MODERATE",
                        "title": f"Incident Record: {acc.severity or 'MODERATE'}",
                        "description": acc.description or f"Historical incident on this road corridor",
                        "datetime": acc.accident_datetime.isoformat() if acc.accident_datetime else None
                    })
                except Exception:
                    continue

    # 2. Also search accidents within the bounding box of start and end coordinates (+ margin)
    min_lat = min(start_lat, end_lat) - 0.015
    max_lat = max(start_lat, end_lat) + 0.015
    min_lng = min(start_lng, end_lng) - 0.015
    max_lng = max(start_lng, end_lng) + 0.015

    nearby_accidents = db.query(Accident).limit(40).all()
    for acc in nearby_accidents:
        if str(acc.accident_id) in [p.get("id") for p in points]:
            continue
        if acc.location is not None:
            try:
                pt = to_shape(acc.location)
                if min_lat <= pt.y <= max_lat and min_lng <= pt.x <= max_lng:
                    points.append({
                        "id": str(acc.accident_id),
                        "latitude": round(pt.y, 6),
                        "longitude": round(pt.x, 6),
                        "type": "historical",
                        "severity": acc.severity or "MODERATE",
                        "title": f"Incident Record: {acc.severity or 'MODERATE'}",
                        "description": acc.description or "Historical accident recorded in this sector",
                        "datetime": acc.accident_datetime.isoformat() if acc.accident_datetime else None
                    })
                    if len(points) >= 8:
                        break
            except Exception:
                continue

    # 3. Always pinpoint the AI Predicted Accident Risk Hazard Spot on the route
    if route_coords and len(route_coords) >= 2:
        # Place hazard marker at the critical midpoint / turning curve along the route
        mid_idx = len(route_coords) // 2
        hazard_lat, hazard_lng = route_coords[mid_idx]
    else:
        hazard_lat = (start_lat + end_lat) / 2.0
        hazard_lng = (start_lng + end_lng) / 2.0

    points.append({
        "id": f"predicted-risk-zone-{round(hazard_lat, 4)}-{round(hazard_lng, 4)}",
        "latitude": round(hazard_lat, 6),
        "longitude": round(hazard_lng, 6),
        "type": "predicted_risk_zone",
        "severity": risk_level,
        "risk_percentage": risk_percentage,
        "title": f"Predicted Accident Risk Zone: {risk_percentage}% ({risk_level})",
        "description": f"AI model evaluated this sector as having {risk_percentage}% incident probability under current road & weather conditions."
    })

    return points

