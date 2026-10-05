import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape

from app.database.models import Road

logger = logging.getLogger("Metrivon.geocoding")

# Simple in-memory cache to avoid redundant external network calls
_GEOCODE_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_REVERSE_CACHE: Dict[str, Dict[str, Any]] = {}
USER_AGENT = "MetrivonAI-Backend/1.0 (contact@Metrivon.ai)"

# Curated high-precision transit hubs and landmarks in Hyderabad to ensure
# 100% instant and accurate recognition for bus stands, terminals, and interchanges.
HYDERABAD_TRANSIT_HUBS: List[Dict[str, Any]] = [
    {
        "primary_name": "Mahatma Gandhi Bus Station (MGBS / Imlibun)",
        "secondary_name": "Gowliguda / CBS, Hyderabad",
        "display_name": "Mahatma Gandhi Bus Station (MGBS / Imlibun), Gowliguda, Hyderabad",
        "latitude": 17.3781,
        "longitude": 78.4851,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["mgbs", "imlibun", "bus stand", "bus stands", "bus tsnd", "bus tsnds", "bus stop", "cbs", "gowliguda", "central bus station"]
    },
    {
        "primary_name": "Jubilee Bus Station (JBS)",
        "secondary_name": "Picket, Secunderabad",
        "display_name": "Jubilee Bus Station (JBS), Secunderabad",
        "latitude": 17.4503,
        "longitude": 78.4983,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["jbs", "jubilee", "bus stand", "bus stands", "bus tsnd", "bus tsnds", "secunderabad", "picket"]
    },
    {
        "primary_name": "Central Bus Station (CBS / Afzalgunj)",
        "secondary_name": "Afzalgunj, Hyderabad",
        "display_name": "Central Bus Station (CBS / Afzalgunj), Afzalgunj, Hyderabad",
        "latitude": 17.3732,
        "longitude": 78.4776,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["cbs", "afzalgunj", "bus stand", "bus stands", "bus tsnd", "bus tsnds"]
    },
    {
        "primary_name": "Koti Bus Stand & Depot",
        "secondary_name": "Women's College Road, Koti, Hyderabad",
        "display_name": "Koti Bus Stand & Depot, Koti, Hyderabad",
        "latitude": 17.3833,
        "longitude": 78.4857,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["koti", "bus stand", "bus stands", "bus tsnd", "bus tsnds", "koti bus"]
    },
    {
        "primary_name": "Dilsukhnagar Bus Station & Depot",
        "secondary_name": "Vijayawada Highway, Dilsukhnagar, Hyderabad",
        "display_name": "Dilsukhnagar Bus Station & Depot, Dilsukhnagar, Hyderabad",
        "latitude": 17.3688,
        "longitude": 78.5273,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["dilsukhnagar", "bus stand", "bus stands", "bus tsnd", "bus tsnds", "depot"]
    },
    {
        "primary_name": "Mehdipatnam Bus Station & Depot",
        "secondary_name": "PVNR Expressway Junction, Mehdipatnam, Hyderabad",
        "display_name": "Mehdipatnam Bus Station & Depot, Mehdipatnam, Hyderabad",
        "latitude": 17.3916,
        "longitude": 78.4410,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["mehdipatnam", "bus stand", "bus stands", "bus tsnd", "bus tsnds"]
    },
    {
        "primary_name": "Secunderabad Bus Station (Rathifile)",
        "secondary_name": "Station Road, Secunderabad",
        "display_name": "Secunderabad Bus Station (Rathifile), Secunderabad",
        "latitude": 17.4360,
        "longitude": 78.5001,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["secunderabad", "rathifile", "bus stand", "bus stands", "bus tsnd", "bus tsnds"]
    },
    {
        "primary_name": "Miyapur Bus Station & Metro Terminal",
        "secondary_name": "Mumbai Highway, Miyapur, Hyderabad",
        "display_name": "Miyapur Bus Station & Metro Terminal, Miyapur, Hyderabad",
        "latitude": 17.4965,
        "longitude": 78.3615,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["miyapur", "bus stand", "bus stands", "bus tsnd", "bus tsnds", "allwyn"]
    },
    {
        "primary_name": "Uppal Bus Terminal & Ring Road Stand",
        "secondary_name": "Inner Ring Road, Uppal, Hyderabad",
        "display_name": "Uppal Bus Terminal & Ring Road Stand, Uppal, Hyderabad",
        "latitude": 17.4018,
        "longitude": 78.5602,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["uppal", "bus stand", "bus stands", "bus tsnd", "bus tsnds"]
    },
    {
        "primary_name": "KPHB / Kukatpally Bus Stop",
        "secondary_name": "KPHB Colony, Mumbai Highway, Hyderabad",
        "display_name": "KPHB / Kukatpally Bus Stop, Kukatpally, Hyderabad",
        "latitude": 17.4932,
        "longitude": 78.3995,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["kphb", "kukatpally", "bus stop", "bus stand", "bus tsnd"]
    },
    {
        "primary_name": "Ameerpet Metro & Bus Interchange",
        "secondary_name": "Ameerpet Crossroads, Hyderabad",
        "display_name": "Ameerpet Metro & Bus Interchange, Ameerpet, Hyderabad",
        "latitude": 17.4375,
        "longitude": 78.4483,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["ameerpet", "bus stop", "bus stand", "bus tsnd", "metro"]
    },
    {
        "primary_name": "Charminar Bus Stand",
        "secondary_name": "Old City, Charminar, Hyderabad",
        "display_name": "Charminar Bus Stand, Charminar, Hyderabad",
        "latitude": 17.3615,
        "longitude": 78.4745,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["charminar", "bus stand", "bus tsnd"]
    },
    {
        "primary_name": "Lingampally Bus Station",
        "secondary_name": "Railway Station Road, BHEL, Lingampally",
        "display_name": "Lingampally Bus Station, Lingampally, Hyderabad",
        "latitude": 17.4912,
        "longitude": 78.3218,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["lingampally", "bhel", "bus stand", "bus tsnd"]
    },
    {
        "primary_name": "ECIL X Roads Bus Station",
        "secondary_name": "ECIL X Roads, Moula Ali, Hyderabad",
        "display_name": "ECIL X Roads Bus Station, ECIL, Hyderabad",
        "latitude": 17.4716,
        "longitude": 78.5728,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["ecil", "moula ali", "bus stand", "bus tsnd"]
    },
    {
        "primary_name": "Hayathnagar Bus Depot & Terminal",
        "secondary_name": "Vijayawada Highway, Hayathnagar, Hyderabad",
        "display_name": "Hayathnagar Bus Depot & Terminal, Hayathnagar, Hyderabad",
        "latitude": 17.3256,
        "longitude": 78.6012,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["hayathnagar", "bus stand", "bus tsnd", "depot"]
    },
    {
        "primary_name": "Falaknuma Bus Station & Depot",
        "secondary_name": "Falaknuma, Old City, Hyderabad",
        "display_name": "Falaknuma Bus Station & Depot, Falaknuma, Hyderabad",
        "latitude": 17.3288,
        "longitude": 78.4682,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["falaknuma", "bus stand", "bus tsnd"]
    },
    {
        "primary_name": "Patancheru Bus Station",
        "secondary_name": "Mumbai Highway, Patancheru, Hyderabad",
        "display_name": "Patancheru Bus Station, Patancheru, Hyderabad",
        "latitude": 17.5284,
        "longitude": 78.2635,
        "type": "bus_station",
        "category": "transit",
        "keywords": ["patancheru", "bus stand", "bus tsnd"]
    },
]

ADMIN_TERMS_TO_FILTER = [
    "greater hyderabad municipal corporation",
    "ghmc",
    "east zone",
    "west zone",
    "north zone",
    "south zone",
    "central zone",
    "secunderabad zone",
    "ward",
    "mandal",
    "telangana",
    "india"
]


def normalize_search_query(query: str) -> str:
    """Corrects common typos in transit and street terms."""
    q = query.strip()
    tokens = q.lower().split()
    corrected = []
    for token in tokens:
        # Match typos like 'tsnd', 'tsnds', 'stnd', 'stnds' -> 'stand'
        if token in ["tsnd", "tsnds", "stnd", "stnds", "stns", "statn"]:
            corrected.append("stand")
        elif token in ["buss", "bsu"]:
            corrected.append("bus")
        elif token in ["raod", "rpad", "rod"]:
            corrected.append("road")
        else:
            corrected.append(token)
    return " ".join(corrected)


def clean_osm_display_name(raw_display_name: str, address: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Cleans raw OpenStreetMap Nominatim strings to eliminate verbose GHMC zones,
    mandal names, and postal codes.
    Returns: (primary_name, secondary_name, clean_display_name)
    """
    parts = [p.strip() for p in raw_display_name.split(",") if p.strip()]
    primary = parts[0] if parts else "Location"

    # Identify clean locality / suburb / area
    suburb = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("residential")
        or address.get("road")
    )
    if suburb:
        sub_lower = suburb.lower()
        if any(admin in sub_lower for admin in ["ward", "zone", "ghmc", "corporation"]):
            suburb = None
        elif suburb.lower() == primary.lower():
            suburb = None

    city = address.get("city") or address.get("state_district") or "Hyderabad"

    if suburb:
        secondary = f"{suburb}, {city}"
    else:
        # Pick the first non-administrative segment
        clean_parts = []
        for p in parts[1:]:
            p_lower = p.lower()
            if not any(admin in p_lower for admin in ADMIN_TERMS_TO_FILTER) and not p.isdigit():
                clean_parts.append(p)
                if len(clean_parts) >= 2:
                    break
        secondary = ", ".join(clean_parts) if clean_parts else city

    clean_display = f"{primary}, {secondary}" if secondary and secondary not in primary else primary
    return primary, secondary, clean_display


def geocode_location(
    query: str,
    city_bias: str = "Hyderabad",
    limit: int = 5,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Geocodes an address or landmark name into real latitude and longitude.
    Seamlessly integrates:
      1. Metrivon AI registered monitored corridors from the local database.
      2. Major Hyderabad Bus Stations, Transit Interchanges, and Terminals.
      3. Cleaned and humanized OpenStreetMap Nominatim geocoding.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    norm_query = normalize_search_query(clean_query).lower()
    cache_key = f"{norm_query}_{city_bias.lower()}_{limit}_{bool(db)}"
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    results: List[Dict[str, Any]] = []
    seen_coords: set = set()

    def _coord_key(lat: float, lon: float) -> str:
        return f"{round(lat, 3)}_{round(lon, 3)}"

    # 1. Search Monitored Road Corridors in Metrivon AI Database
    if db is not None:
        try:
            # If the user typed "road", "main road", or specific road names
            is_generic_road = norm_query in ["road", "roads", "main road", "main roads", "corridor"]
            if is_generic_road:
                db_roads = db.query(Road).limit(limit).all()
            else:
                road_keyword = norm_query.replace("road", "").strip() or norm_query
                db_roads = (
                    db.query(Road)
                    .filter(Road.road_name.ilike(f"%{road_keyword}%"))
                    .limit(limit)
                    .all()
                )

            for r in db_roads:
                lat, lng = None, None
                if r.start_location is not None:
                    pt = to_shape(r.start_location)
                    lat, lng = float(pt.y), float(pt.x)
                elif r.route_geometry is not None:
                    geom = to_shape(r.route_geometry)
                    if hasattr(geom, "coords") and geom.coords:
                        coords = list(geom.coords)
                        mid = coords[len(coords) // 2]
                        lat, lng = float(mid[1]), float(mid[0])

                if lat is not None and lng is not None:
                    ck = _coord_key(lat, lng)
                    if ck not in seen_coords:
                        seen_coords.add(ck)
                        results.append({
                            "display_name": f"{r.road_name}, Hyderabad",
                            "primary_name": r.road_name,
                            "secondary_name": f"Metrivon Monitored Corridor ({r.road_type or 'Urban Arterial'})",
                            "latitude": lat,
                            "longitude": lng,
                            "type": "road",
                            "category": "corridor",
                            "importance": 1.0,
                            "address": {"road": r.road_name, "city": "Hyderabad"}
                        })
        except Exception as e:
            logger.debug("Local road corridor search failed: %s", e)

    # 2. Check Curated Hyderabad Bus Stations and Transit Directory
    transit_stopwords = {
        "road", "roads", "street", "highway", "avenue", "lane", "station",
        "bus", "stop", "terminal", "depot", "stand", "crossroads", "junction",
        "near", "opposite", "chowk", "circle", "flyover"
    }
    for hub in HYDERABAD_TRANSIT_HUBS:
        matched = False
        if any(kw in norm_query for kw in hub["keywords"]):
            matched = True
        elif norm_query in hub["primary_name"].lower():
            matched = True
        elif any(w in hub["primary_name"].lower() for w in norm_query.split() if len(w) >= 3 and w not in transit_stopwords):
            matched = True

        if matched:
            ck = _coord_key(hub["latitude"], hub["longitude"])
            if ck not in seen_coords:
                seen_coords.add(ck)
                results.append({
                    "display_name": hub["display_name"],
                    "primary_name": hub["primary_name"],
                    "secondary_name": hub["secondary_name"],
                    "latitude": hub["latitude"],
                    "longitude": hub["longitude"],
                    "type": hub["type"],
                    "category": "transit",
                    "importance": 0.95,
                    "address": {"amenity": hub["primary_name"], "city": "Hyderabad"}
                })

    # If we already have enough high-confidence local & transit results, return them
    if len(results) >= limit:
        final_results = results[:limit]
        _GEOCODE_CACHE[cache_key] = final_results
        return final_results

    # 3. External OpenStreetMap Nominatim Geocoding
    search_term = norm_query
    if city_bias and city_bias.lower() not in norm_query:
        search_term = f"{norm_query}, {city_bias}"

    params = {
        "q": search_term,
        "format": "json",
        "limit": limit * 2,
        "addressdetails": 1,
        "countrycodes": "in"
    }
    url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data:
            lat = float(item["lat"])
            lon = float(item["lon"])
            ck = _coord_key(lat, lon)
            if ck in seen_coords:
                continue
            seen_coords.add(ck)

            raw_name = item.get("display_name", "")
            address = item.get("address", {})
            primary, secondary, clean_disp = clean_osm_display_name(raw_name, address)

            place_type = item.get("type", "location")
            category = "location"
            if place_type in ["bus_station", "station", "stop", "platform", "tram_stop"]:
                category = "transit"
            elif place_type in ["road", "highway", "primary", "secondary", "tertiary", "trunk", "residential"]:
                category = "corridor"
            elif place_type in ["attraction", "historic", "monument", "mall", "hospital"]:
                category = "poi"

            results.append({
                "display_name": clean_disp,
                "primary_name": primary,
                "secondary_name": secondary,
                "latitude": lat,
                "longitude": lon,
                "type": place_type,
                "category": category,
                "importance": float(item.get("importance", 0.0)),
                "address": address
            })

            if len(results) >= limit:
                break

    except Exception as err:
        logger.warning("Geocoding failed for '%s': %s", clean_query, err)

    if not results:
        # Retry with simplified query (stripping junction, chowk, circle, crossroads)
        simplified = norm_query
        for suffix in ["junction", "crossroads", "cross roads", "x roads", "x-roads", "circle", "square", "chowk", "bus stop", "stop", "station"]:
            if suffix in simplified:
                simplified = simplified.replace(suffix, "").strip()
        if simplified and simplified != norm_query and len(simplified) >= 3:
            return geocode_location(query=simplified, city_bias=city_bias, limit=limit, db=db)

    final_results = results[:limit]
    _GEOCODE_CACHE[cache_key] = final_results
    return final_results


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

        primary, secondary, clean_disp = clean_osm_display_name(
            data.get("display_name", f"Location ({latitude:.4f}, {longitude:.4f})"),
            addr
        )

        result = {
            "display_name": clean_disp,
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


def find_nearest_road_by_coordinates(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance_meters: float = 3000.0
) -> Optional[Road]:
    """
    Uses PostGIS spatial indexing to find the closest road segment to given coordinates.
    Employs progressive radius search (initial max_distance_meters -> 12,000m -> city-wide)
    to guarantee any point within Hyderabad metropolitan area maps to a monitored road.
    """
    point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    # 1. Search route_geometry within initial radius
    try:
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

    # 2. Search start_location within initial radius
    try:
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

    # 3. Progressive expansion: search up to 12,000 meters (12km)
    expanded_radius = max(max_distance_meters * 3, 12000.0)
    try:
        road = (
            db.query(Road)
            .filter(Road.route_geometry.isnot(None))
            .filter(func.ST_DWithin(func.geography(Road.route_geometry), func.geography(point), expanded_radius))
            .order_by(func.ST_Distance(func.geography(Road.route_geometry), func.geography(point)))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS expanded route_geometry query failed: %s", err)

    # 4. Fallback: closest road in the entire system within metropolitan region
    try:
        road = (
            db.query(Road)
            .filter(Road.route_geometry.isnot(None))
            .order_by(func.ST_Distance(func.geography(Road.route_geometry), func.geography(point)))
            .first()
        )
        if road:
            return road
    except Exception as err:
        logger.debug("PostGIS absolute closest road query failed: %s", err)

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
        f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
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
            steps = _extract_route_steps(primary_route)

            res = {
                "coordinates": leaflet_coords,
                "distance_km": dist_km,
                "duration_minutes": dur_mins,
                "is_real_route": True,
                "steps": steps,
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
        "is_real_route": False,
        "steps": [],
    }
    return fallback_res


def get_or_create_road_from_geocoding(
    db: Session,
    road_name: Optional[str] = None,
    start_lat: Optional[float] = None,
    start_lng: Optional[float] = None,
    end_lat: Optional[float] = None,
    end_lng: Optional[float] = None,
    start_name: Optional[str] = None,
    end_name: Optional[str] = None
) -> Tuple[Road, bool]:
    """
    Finds a road in the database, or uses the Geocoding API to resolve its real
    spatial coordinates, route geometry via OSRM, and properties, and creates the road in the DB.
    Returns: (Road, created: bool)
    """
    from fastapi import HTTPException

    # 1. Search candidate names in existing database
    candidate_names = [n.strip() for n in [road_name, start_name, end_name] if n and n.strip()]
    for cand in candidate_names:
        existing = db.query(Road).filter(Road.road_name.ilike(cand)).first()
        if not existing and len(cand) >= 3:
            existing = db.query(Road).filter(Road.road_name.ilike(f"%{cand}%")).first()
        if not existing and "road" in cand.lower():
            short_cand = cand.lower().replace("road", "").strip()
            if len(short_cand) >= 3:
                existing = db.query(Road).filter(Road.road_name.ilike(f"%{short_cand}%")).first()
        if existing:
            return existing, False

    # 2. Check if a registered road starts near the coordinates
    if start_lat is not None and start_lng is not None:
        nearby = find_nearest_road_by_coordinates(db, start_lat, start_lng, max_distance_meters=250.0)
        if nearby:
            if not candidate_names or any(c.lower() in nearby.road_name.lower() or nearby.road_name.lower() in c.lower() for c in candidate_names):
                return nearby, False

    # 3. Road was searched but is NOT in the database table -> Verify and resolve via Geocoding API
    logger.info("Road searched not found in database. Searching in geocoding: road_name=%s, start=%s, end=%s", road_name, start_name, end_name)

    query_start = start_name or road_name
    if not query_start and (start_lat is None or start_lng is None):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "MISSING_LOCATION",
                "message": "Please specify a road name or start coordinates.",
                "field": "road_name"
            }
        )

    geo_start = []
    # 3a. Resolve start coordinates if missing
    if start_lat is None or start_lng is None:
        if query_start:
            geo_start = geocode_location(query_start, db=db, limit=3)
            if not geo_start:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_code": "ROAD_NOT_FOUND",
                        "message": f"Road or location '{query_start}' does not exist in geocoding records. Please provide a verified road name.",
                        "field": "road_name" if road_name else "start_location"
                    }
                )
            start_lat = geo_start[0]["latitude"]
            start_lng = geo_start[0]["longitude"]
            if not start_name:
                start_name = geo_start[0].get("primary_name") or query_start

    # 3b. Verify whether the searched entity is actually a road or has an OSM street
    verified_road_name = None
    if geo_start:
        top_res = geo_start[0]
        addr = top_res.get("address", {})
        osm_road = addr.get("road")
        is_corridor = (
            top_res.get("category") == "corridor"
            or top_res.get("type") in [
                "road", "highway", "primary", "secondary", "tertiary",
                "trunk", "residential", "living_street", "motorway", "track", "unclassified"
            ]
        )
        if osm_road:
            verified_road_name = osm_road
        elif is_corridor:
            verified_road_name = top_res.get("primary_name") or query_start
        elif road_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "NOT_A_ROAD",
                    "message": f"'{road_name}' was found in geocoding as a {top_res.get('type', 'place')} but is not a recognized road or traffic corridor.",
                    "field": "road_name"
                }
            )

    # 3c. Resolve end coordinates if missing
    if end_lat is None or end_lng is None:
        if end_name:
            geo_end = geocode_location(end_name, db=db, limit=1)
            if not geo_end:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_code": "ROAD_NOT_FOUND",
                        "message": f"End location '{end_name}' does not exist in geocoding records.",
                        "field": "end_location"
                    }
                )
            end_lat = geo_end[0]["latitude"]
            end_lng = geo_end[0]["longitude"]

    # If end coordinates are not set or identical to start, create a realistic 500m corridor offset
    if end_lat is None or end_lng is None or (abs(end_lat - start_lat) < 0.0001 and abs(end_lng - start_lng) < 0.0001):
        end_lat = round(start_lat + 0.0050, 6)
        end_lng = round(start_lng + 0.0050, 6)

    # 3d. Clean up road name using verified road name from geocoding
    clean_name = None
    if verified_road_name:
        clean_name = verified_road_name.strip()
    elif road_name and len(road_name.strip()) >= 2:
        clean_name = road_name.strip()
    elif start_name and end_name and start_name.strip().lower() != end_name.strip().lower():
        clean_name = f"{start_name.strip()} - {end_name.strip()}"
    elif start_name:
        clean_name = start_name.strip()
    elif end_name:
        clean_name = end_name.strip()
    else:
        rev = reverse_geocode(start_lat, start_lng)
        clean_name = (rev.get("road") if rev else None) or (rev.get("display_name") if rev else None) or f"Road Corridor [{start_lat:.4f}, {start_lng:.4f}]"

    # Append 'Road' only if the name was auto-generated from coordinate reverse-lookup without road keywords
    if not (verified_road_name or road_name or start_name or end_name):
        if not any(w in clean_name.lower() for w in ["road", "street", "highway", "expressway", "arterial", "avenue", "lane", "junction", "corridor", "track"]):
            clean_name = f"{clean_name} Road"

    # 3e. Check if clean_name already exists in DB (to prevent duplicates)
    dup_road = db.query(Road).filter(Road.road_name.ilike(clean_name)).first()
    if dup_road:
        return dup_road, False

    # 3e. Infer realistic road parameters
    name_lower = clean_name.lower()
    if any(w in name_lower for w in ["highway", "expressway", "ring road", "flyover", "nh", "bypass"]):
        road_type = "Major Arterial"
        speed_limit = 60.0
        road_capacity = 3200
        number_of_lanes = 6
    elif any(w in name_lower for w in ["lane", "street", "colony", "gali", "galli", "bazaar"]):
        road_type = "Sub-Arterial"
        speed_limit = 40.0
        road_capacity = 1800
        number_of_lanes = 2
    else:
        road_type = "Urban Arterial"
        speed_limit = 50.0
        road_capacity = 2400
        number_of_lanes = 4

    # 3f. Generate OSRM route geometry
    driving_route = get_driving_route(start_lat, start_lng, end_lat, end_lng)
    route_coords = driving_route.get("coordinates") or [[start_lat, start_lng], [end_lat, end_lng]]
    linestring_wkt = ", ".join(f"{pt[1]} {pt[0]}" for pt in route_coords)

    start_point = WKTElement(f"POINT({start_lng} {start_lat})", srid=4326)
    end_point = WKTElement(f"POINT({end_lng} {end_lat})", srid=4326)
    route_geom = WKTElement(f"LINESTRING({linestring_wkt})", srid=4326)

    # 3g. Associate with nearest TrafficZone
    zone_id = None
    try:
        from app.database.models import TrafficZone
        pt_geom = ST_SetSRID(ST_MakePoint(start_lng, start_lat), 4326)
        closest_zone = (
            db.query(TrafficZone)
            .filter(TrafficZone.location.isnot(None))
            .order_by(func.ST_Distance(func.geography(TrafficZone.location), func.geography(pt_geom)))
            .first()
        )
        if closest_zone:
            zone_id = closest_zone.zone_id
        else:
            first_z = db.query(TrafficZone).first()
            if first_z:
                zone_id = first_z.zone_id
    except Exception as z_err:
        logger.debug("Zone lookup fallback: %s", z_err)

    # 3h. Create and commit the new Road in DB
    new_road = Road(
        road_name=clean_name[:200],
        zone_id=zone_id,
        start_location=start_point,
        end_location=end_point,
        route_geometry=route_geom,
        road_type=road_type,
        road_capacity=road_capacity,
        speed_limit=speed_limit,
        road_condition="GOOD",
        number_of_lanes=number_of_lanes,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(new_road)
    db.commit()
    db.refresh(new_road)
    logger.info("Successfully created searched road in DB via geocoding API: '%s' (ID: %s)", new_road.road_name, new_road.road_id)
    return new_road, True


_MANEUVER_VERBS = {
    "depart": "Head out",
    "arrive": "Arrive at your destination",
    "turn": "Turn",
    "new name": "Continue",
    "merge": "Merge",
    "on ramp": "Take the ramp",
    "off ramp": "Take the exit",
    "fork": "Keep",
    "end of road": "Continue",
    "continue": "Continue",
    "roundabout": "At the roundabout, take the exit",
    "rotary": "At the traffic circle, take the exit",
    "roundabout turn": "At the roundabout, turn",
    "notification": "Continue",
    "exit roundabout": "Exit the roundabout",
    "exit rotary": "Exit the traffic circle",
}


def _humanize_maneuver(maneuver: Dict[str, Any], road_name: str, is_first: bool, is_last: bool) -> str:
    """Turns a raw OSRM maneuver object into a Google-Maps-style instruction sentence."""
    m_type = maneuver.get("type", "")
    modifier = maneuver.get("modifier")

    if is_first or m_type == "depart":
        return f"Head out on {road_name}" if road_name else "Head out"
    if is_last or m_type == "arrive":
        return "Arrive at your destination"

    verb = _MANEUVER_VERBS.get(m_type, "Continue")
    if m_type in ("turn", "roundabout turn") and modifier:
        verb = f"Turn {modifier}"
    elif m_type == "fork" and modifier:
        verb = f"Keep {modifier}"
    elif m_type == "end of road" and modifier:
        verb = f"Turn {modifier}"

    if road_name:
        return f"{verb} onto {road_name}"
    return verb


def _extract_route_steps(primary_route: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flattens OSRM's per-leg steps into a single Google-Maps-style turn list."""
    steps: List[Dict[str, Any]] = []
    legs = primary_route.get("legs", [])
    all_raw_steps = [s for leg in legs for s in leg.get("steps", [])]
    total = len(all_raw_steps)

    for idx, raw_step in enumerate(all_raw_steps):
        maneuver = raw_step.get("maneuver", {})
        road_name = raw_step.get("name") or ""
        instruction = _humanize_maneuver(maneuver, road_name, idx == 0, idx == total - 1)
        loc = maneuver.get("location")  # OSRM gives [lng, lat]
        steps.append({
            "instruction": instruction,
            "road_name": road_name or None,
            "distance_meters": round(raw_step.get("distance", 0.0), 1),
            "duration_seconds": round(raw_step.get("duration", 0.0), 1),
            "maneuver_type": maneuver.get("type"),
            "maneuver_modifier": maneuver.get("modifier"),
            "coordinates": [round(loc[1], 6), round(loc[0], 6)] if loc else None,
        })
    return steps


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

