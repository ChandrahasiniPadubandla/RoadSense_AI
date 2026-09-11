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


def find_nearest_road_by_coordinates(db: Session, latitude: float, longitude: float) -> Optional[Road]:
    """
    Uses PostGIS spatial indexing to find the closest road segment to given coordinates.
    Falls back safely to point distance if route_geometry is missing.
    """
    try:
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        # 1. Try finding closest road geometry
        road = (
            db.query(Road)
            .filter(Road.route_geometry.isnot(None))
            .order_by(ST_Distance(Road.route_geometry, point))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS route_geometry distance query failed: %s", err)

    # 2. Try start_location point distance
    try:
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        road = (
            db.query(Road)
            .filter(Road.start_location.isnot(None))
            .order_by(ST_Distance(Road.start_location, point))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS start_location distance query failed: %s", err)

    # 3. Python-level fallback for geometry shapes
    all_roads = db.query(Road).filter(Road.start_location.isnot(None)).all()
    best_dist = float("inf")
    best_road = None
    for r in all_roads:
        try:
            pt = to_shape(r.start_location)
            d = (pt.y - latitude) ** 2 + (pt.x - longitude) ** 2
            if d < best_dist:
                best_dist = d
                best_road = r
        except Exception:
            continue

    return best_road
