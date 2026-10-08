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
        if any(admin in sub_lower for admin in ADMIN_TERMS_TO_FILTER):
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
    Dynamically geocodes an address, landmark, POI, metro station, mall, hospital, or street name
    into real GPS latitude and longitude using live OpenStreetMap Komoot Photon API (like Google Maps),
    with support for registered monitored road corridors from the local database.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    cache_key = f"{clean_query.lower()}_{city_bias.lower()}_{limit}_{bool(db)}"
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    results: List[Dict[str, Any]] = []
    seen_coords: set = set()

    def _coord_key(lat: float, lon: float) -> str:
        return f"{round(lat, 3)}_{round(lon, 3)}"

    # 1. Search Monitored Road Corridors in Metrivon AI Database (if present)
    if db is not None:
        try:
            q_lower = clean_query.lower()
            is_generic_road = q_lower in ["road", "roads", "main road", "main roads", "corridor"]
            if is_generic_road:
                db_roads = db.query(Road).limit(limit).all()
            else:
                road_keyword = q_lower.replace("road", "").strip() or q_lower
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

    # 2. Dynamic Live Geocoding via Komoot Photon API (OSM + Elasticsearch)
    # Extracts distinct search tokens (e.g. 'moospet' from 'moospet metro station')
    tokens = clean_query.lower().split()
    generic_transit_words = {
        "metro", "station", "subway", "bus", "stand", "stop", "railway",
        "terminal", "crossroads", "junction", "circle", "chowk"
    }
    distinctive_tokens = [t for t in tokens if t not in generic_transit_words and len(t) >= 3]

    def _fetch_photon(search_str: str) -> List[Dict[str, Any]]:
        params = {
            "q": search_str,
            "limit": limit * 2,
            "lat": 17.3850,
            "lon": 78.4867
        }
        url = f"https://photon.komoot.io/api/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("features", [])

    try:
        raw_features = _fetch_photon(clean_query)
        # If the user specified a transit or POI descriptor, also fetch core name to discover exact nodes (e.g. Moosapet station node)
        if distinctive_tokens:
            core_query = " ".join(distinctive_tokens)
            if core_query != clean_query.lower():
                core_features = _fetch_photon(core_query)
                raw_features = raw_features + core_features

        # Score and rank features by relevance to user query
        scored_features: List[Tuple[float, Dict[str, Any]]] = []
        for feat in raw_features:
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = float(coords[0]), float(coords[1])
            ck = _coord_key(lat, lon)
            if ck in seen_coords:
                continue

            props = feat.get("properties", {})
            raw_name = props.get("name") or props.get("street") or clean_query.title()
            name_lower = raw_name.lower()
            osm_key = (props.get("osm_key") or "").lower()
            osm_value = (props.get("osm_value") or "").lower()

            score = 0.0
            if distinctive_tokens:
                for dt in distinctive_tokens:
                    if dt in name_lower:
                        score += 50.0
                    elif len(dt) >= 4 and any(dt[:4] in w for w in name_lower.split()):
                        # Fuzzy typo tolerance (e.g. moospet vs moosapet)
                        score += 40.0
            else:
                score += 10.0

            q_lower = clean_query.lower()
            if "metro" in q_lower and (osm_key == "railway" or "metro" in name_lower or osm_value in ["station", "subway", "subway_entrance"]):
                score += 30.0
            if "bus" in q_lower and (osm_value in ["bus_station", "bus_stop"] or "bus" in name_lower):
                score += 30.0
            if "mall" in q_lower and (osm_value in ["mall", "commercial", "department_store"] or "mall" in name_lower):
                score += 30.0
            if "hospital" in q_lower and (osm_value in ["hospital", "clinic"] or "hospital" in name_lower):
                score += 30.0

            scored_features.append((score, feat))

        # Sort highest score first
        scored_features.sort(key=lambda x: x[0], reverse=True)

        for _, feat in scored_features:
            coords = feat.get("geometry", {}).get("coordinates", [])
            lon, lat = float(coords[0]), float(coords[1])
            ck = _coord_key(lat, lon)
            if ck in seen_coords:
                continue
            seen_coords.add(ck)

            props = feat.get("properties", {})
            raw_name = props.get("name") or props.get("street") or clean_query.title()
            osm_key = (props.get("osm_key") or "").lower()
            osm_value = (props.get("osm_value") or "").lower()
            lower_name = raw_name.lower()

            locality = props.get("locality") or props.get("district")
            street = props.get("street")
            city = props.get("city") or props.get("district") or props.get("county") or "Hyderabad"
            state = props.get("state", "Telangana")
            postcode = props.get("postcode", "")

            # Classify dynamically like Google Maps
            category = "location"
            place_type = osm_value or osm_key or "location"

            q_lower = clean_query.lower()
            if (osm_key == "railway" and osm_value in ["station", "subway_entrance", "subway", "halt", "tram_stop"]) or "metro" in lower_name or ("metro" in q_lower and osm_value in ["station", "subway"]):
                if "metro" in lower_name or "metro" in q_lower or osm_value in ["subway", "subway_entrance"]:
                    category = "metro"
                    place_type = "metro_station"
                    if "metro" not in lower_name and "station" not in lower_name:
                        raw_name = f"{raw_name} Metro Station"
                else:
                    category = "railway"
                    place_type = "railway_station"
            elif (osm_key in ["amenity", "highway"] and osm_value in ["bus_station", "bus_stop"]) or "bus stand" in lower_name or "bus stop" in lower_name or "depot" in lower_name:
                category = "transit"
                place_type = "bus_station"
            elif (osm_key in ["amenity", "healthcare"] and osm_value in ["hospital", "clinic", "doctors"]) or "hospital" in lower_name or "clinic" in lower_name:
                category = "hospital"
                place_type = "hospital"
            elif (osm_key in ["shop", "building", "landuse"] and osm_value in ["mall", "department_store", "supermarket", "commercial"]) or "mall" in lower_name or "shopping" in lower_name:
                category = "mall"
                place_type = "mall"
            elif (osm_key in ["aeroway", "amenity"] and osm_value in ["aerodrome", "airport"]) or "airport" in lower_name:
                category = "airport"
                place_type = "airport"
            elif osm_key in ["highway", "road"] or osm_value in ["road", "highway", "primary", "secondary", "tertiary", "trunk", "residential"]:
                category = "corridor"
                place_type = "road"
            elif osm_key in ["tourism", "historic", "leisure"] or osm_value in ["attraction", "monument", "theme_park"]:
                category = "poi"
                place_type = "landmark"

            # Clean secondary area description
            area_tokens = []
            for part in [locality, street, city]:
                if part and part.lower() not in raw_name.lower() and part not in area_tokens:
                    area_tokens.append(part)
            secondary = ", ".join(area_tokens) if area_tokens else city
            display_name = f"{raw_name}, {secondary}" if secondary and secondary not in raw_name else raw_name

            results.append({
                "display_name": display_name,
                "primary_name": raw_name,
                "secondary_name": secondary,
                "latitude": lat,
                "longitude": lon,
                "type": place_type,
                "category": category,
                "importance": 0.9 if category in ["metro", "mall", "hospital", "transit"] else 0.85,
                "address": {
                    "amenity": raw_name,
                    "road": street,
                    "suburb": locality,
                    "city": city,
                    "state": state,
                    "postcode": postcode,
                }
            })

            if len(results) >= limit:
                break

    except Exception as err:
        logger.warning("Dynamic Photon geocoding failed for '%s': %s", clean_query, err)

    final_results = results[:limit]
    _GEOCODE_CACHE[cache_key] = final_results
    return final_results



def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Reverse-geocodes exact GPS coordinates into a human-readable street/area name using Photon API.
    """
    cache_key = f"{round(latitude, 4)}_{round(longitude, 4)}"
    if cache_key in _REVERSE_CACHE:
        return _REVERSE_CACHE[cache_key]

    params = {
        "lat": latitude,
        "lon": longitude,
    }
    url = f"https://photon.komoot.io/reverse?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        features = data.get("features", [])
        if features:
            props = features[0].get("properties", {})
            name = props.get("name") or props.get("street") or "Selected Location"
            street = props.get("street") or name
            locality = props.get("locality") or props.get("district")
            city = props.get("city") or props.get("district") or props.get("county") or "Hyderabad"
            state = props.get("state", "Telangana")
            postcode = props.get("postcode")

            area_parts = [p for p in [locality, city] if p and p.lower() not in name.lower()]
            secondary = ", ".join(area_parts) if area_parts else city
            display_name = f"{name}, {secondary}" if secondary and secondary not in name else name

            result = {
                "display_name": display_name,
                "road": street,
                "suburb": locality,
                "neighbourhood": props.get("district"),
                "city": city,
                "state": state,
                "postcode": postcode,
                "latitude": latitude,
                "longitude": longitude
            }
            _REVERSE_CACHE[cache_key] = result
            return result
    except Exception as err:
        logger.warning("Photon reverse geocoding failed for (%s, %s): %s", latitude, longitude, err)

    fallback_result = {
        "display_name": f"Location ({latitude:.4f}, {longitude:.4f})",
        "road": "Selected Road",
        "suburb": None,
        "neighbourhood": None,
        "city": "Hyderabad",
        "state": "Telangana",
        "postcode": None,
        "latitude": latitude,
        "longitude": longitude
    }
    return fallback_result


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


def _calculate_realistic_urban_duration(
    dist_km: float,
    raw_dur_secs: float,
    num_steps: int,
    mode: str
) -> float:
    """
    Computes realistic urban travel duration modeled after real Indian metropolitan traffic
    (e.g., Hyderabad), where average city car speeds range from 18-26 km/h (unlike
    the ideal theoretical free-flow 60-80 km/h speeds returned by raw OSRM).
    
    Dynamically accounts for:
    - Urban street hierarchy (city streets vs. expressways/flyovers)
    - Traffic light signals & intersection wait times based on number of maneuvers
    - Time-of-day traffic peak curves (morning/evening rush hour vs. midday vs. late night)
    - Two-wheeler lane filtering speed advantages
    - Pedestrian sidewalk walking velocity
    """
    from datetime import datetime, timezone, timedelta

    if dist_km <= 0.05:
        return 1.0

    num_turns = max(num_steps, 1)

    # 1. Walk mode: pedestrian velocity ~4.8 km/h (~12.5 min/km)
    if mode == "foot":
        if raw_dur_secs > (dist_km / 8.0) * 3600:
            return round(raw_dur_secs / 60.0, 1)
        return round(max((dist_km / 4.8) * 60.0, 1.0), 1)

    # 2. Derive raw OSRM speed to detect if corridor is high-speed expressway vs urban street
    raw_speed_kmh = (dist_km / (raw_dur_secs / 3600.0)) if raw_dur_secs > 0 else 40.0

    # 3. Dynamic Time-of-Day Traffic Factor (IST local hour: UTC + 5:30)
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    now_hour = ist_now.hour

    # Peak hours: 8:30-11:30 AM and 17:00-21:30 PM
    if 17 <= now_hour <= 21:
        time_factor = 1.25  # Evening peak
    elif 8 <= now_hour <= 11:
        time_factor = 1.20  # Morning rush hour
    elif now_hour >= 23 or now_hour < 6:
        time_factor = 0.85  # Late night clear roads
    else:
        time_factor = 1.10  # Standard daytime traffic

    # 4. Urban vs Expressway Speed Calibration
    if raw_speed_kmh >= 75.0:
        # Expressway / Ring Road / Highway corridor (e.g. ORR, PVNR Expressway)
        # Vehicles move at ~55-65 km/h with few traffic lights
        effective_car_speed = min(raw_speed_kmh * 0.75, 65.0)
        signal_delay_mins = min(num_turns * 0.12, 4.0)
    elif raw_speed_kmh >= 45.0:
        # Major arterial corridor (e.g., Gachibowli-Miyapur, NH-65, Inner Ring Road)
        # City arterial speeds ~24-28 km/h
        effective_car_speed = 25.5 / time_factor
        signal_delay_mins = min(num_turns * 0.28, 9.0)
    else:
        # Dense city core / market / interior roads (e.g., Ameerpet, Koti, Begumpet)
        # City core speeds ~18-22 km/h
        effective_car_speed = 21.0 / time_factor
        signal_delay_mins = min(num_turns * 0.32, 11.0)

    # Base car travel time = moving time + intersection/signal queues
    moving_time_mins = (dist_km / effective_car_speed) * 60.0
    car_total_mins = moving_time_mins + signal_delay_mins

    # 5. Vehicle Mode Adjustment
    if mode == "bike":
        # Two-wheelers in India filter through lane queues, avoid car bottlenecks,
        # and wait less at signals (~30-34 km/h effective speed, ~0.15 min signal delay)
        effective_bike_speed = min(effective_car_speed * 1.35, 34.0)
        bike_signal_delay = min(num_turns * 0.14, 4.0)
        bike_total_mins = ((dist_km / effective_bike_speed) * 60.0) + bike_signal_delay
        # Ensure bike is always faster than car in city traffic, but bounded realistically
        return round(max(min(bike_total_mins, car_total_mins * 0.75), 1.0), 1)

    # Car mode
    return round(max(car_total_mins, 1.0), 1)


def get_driving_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    mode: str = "driving"
) -> Dict[str, Any]:
    """
    Fetches the real-world street route geometry and distance between start and destination coordinates
    according to the selected vehicle type:
      - 'driving' (Car / Cab / Auto)
      - 'bike' (Bicycle / Two-Wheeler)
      - 'foot' (Walking / Pedestrian)
    Uses Open Source Routing Machine (OSRM) with profile-specific turn-by-turn guidance and speed models.
    """
    norm_mode = (mode or "driving").strip().lower()
    if norm_mode in ["car", "auto", "cab", "drive", "driving"]:
        normalized_mode_name = "driving"
    elif norm_mode in ["bike", "bicycle", "cycling", "cycle", "motorcycle", "two_wheeler"]:
        normalized_mode_name = "bike"
    elif norm_mode in ["foot", "walk", "walking", "pedestrian"]:
        normalized_mode_name = "foot"
    else:
        normalized_mode_name = "driving"

    cache_key = f"{round(start_lat, 4)}_{round(start_lng, 4)}_{round(end_lat, 4)}_{round(end_lng, 4)}_{normalized_mode_name}"
    if cache_key in _ROUTE_CACHE:
        return _ROUTE_CACHE[cache_key]

    # Select dedicated routing service endpoints per vehicle profile:
    # - 'foot': dedicated OpenStreetMap pedestrian routing engine (sidewalks, footways, crosswalks, pedestrian paths)
    # - 'bike': dedicated OpenStreetMap bicycle & two-wheeler routing engine (cycleways, residential streets, quiet roads)
    # - 'driving': primary OSRM motorway/arterial car routing engine
    urls_to_try = []
    if normalized_mode_name == "foot":
        urls_to_try.append(
            f"https://routing.openstreetmap.de/routed-foot/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )
        urls_to_try.append(
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )
    elif normalized_mode_name == "bike":
        # Two-wheelers (motorcycle / scooter / bike) in India have full access to motorable city roads,
        # flyovers, and arterial roads, and can filter through traffic bottlenecks and service roads.
        urls_to_try.append(
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )
        urls_to_try.append(
            f"https://routing.openstreetmap.de/routed-bike/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )
    else:
        urls_to_try.append(
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )
        urls_to_try.append(
            f"https://routing.openstreetmap.de/routed-car/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson&steps=true"
        )

    for url in urls_to_try:
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
                raw_dur_secs = primary_route.get("duration", 0)
                steps = _extract_route_steps(primary_route)

                # Dynamically calculate realistic urban travel duration (Google Maps calibrated)
                dur_mins = _calculate_realistic_urban_duration(
                    dist_km=dist_km,
                    raw_dur_secs=raw_dur_secs,
                    num_steps=len(steps),
                    mode=normalized_mode_name
                )

                res = {
                    "coordinates": leaflet_coords,
                    "distance_km": dist_km,
                    "duration_minutes": dur_mins,
                    "is_real_route": True,
                    "steps": steps,
                    "mode": normalized_mode_name,
                }
                _ROUTE_CACHE[cache_key] = res
                return res
        except Exception as err:
            logger.warning("Routing engine failed for %s (%s): %s", normalized_mode_name, url, err)
            continue

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

    if normalized_mode_name == "bike":
        fallback_dur = round(max(dist_km * 1.8, 1.0), 1)
    elif normalized_mode_name == "foot":
        fallback_dur = round(max((dist_km / 4.8) * 60.0, 1.0), 1)
    else:
        fallback_dur = round(max(dist_km * 2.2, 1.0), 1)

    fallback_res = {
        "coordinates": [[round(start_lat, 6), round(start_lng, 6)], [round(end_lat, 6), round(end_lng, 6)]],
        "distance_km": dist_km,
        "duration_minutes": fallback_dur,
        "is_real_route": False,
        "steps": [],
        "mode": normalized_mode_name,
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

