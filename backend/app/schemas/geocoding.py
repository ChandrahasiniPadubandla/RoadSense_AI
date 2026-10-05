from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class GeocodeSearchResult(BaseModel):
    display_name: str = Field(..., description="Full formatted address/name from OpenStreetMap or Metrivon database")
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    type: Optional[str] = Field(default="location", description="Type of place (e.g. suburb, road, amenity)")
    importance: Optional[float] = Field(default=0.0, description="Relevance score")
    address: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Address breakdown")
    primary_name: Optional[str] = Field(default=None, description="Concise primary landmark or road name")
    secondary_name: Optional[str] = Field(default=None, description="Clean area, locality, or category description")
    category: Optional[str] = Field(default="location", description="Category: 'corridor' | 'transit' | 'poi' | 'location'")


class ReverseGeocodeResult(BaseModel):
    display_name: str = Field(..., description="Full address string")
    road: Optional[str] = Field(default=None, description="Street or road name")
    suburb: Optional[str] = Field(default=None, description="Locality or suburb")
    neighbourhood: Optional[str] = Field(default=None, description="Neighbourhood name")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State")
    postcode: Optional[str] = Field(default=None, description="Postal code")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")


class NearestRoadResult(BaseModel):
    road_id: UUID
    road_name: str
    road_type: Optional[str] = None
    speed_limit: Optional[float] = None
    road_capacity: Optional[int] = None
    number_of_lanes: Optional[int] = None
    road_condition: Optional[str] = None


class RouteStep(BaseModel):
    instruction: str = Field(..., description="Human-readable turn-by-turn instruction, e.g. 'Turn right onto Banjara Hills Road'")
    road_name: Optional[str] = Field(default=None, description="Name of the road for this step, if known")
    distance_meters: float = Field(..., description="Length of this step in meters")
    duration_seconds: float = Field(..., description="Estimated time for this step in seconds")
    maneuver_type: Optional[str] = Field(default=None, description="Raw OSRM maneuver type, e.g. 'turn', 'depart', 'arrive'")
    maneuver_modifier: Optional[str] = Field(default=None, description="Raw OSRM maneuver modifier, e.g. 'left', 'right', 'straight'")
    coordinates: Optional[List[float]] = Field(default=None, description="[latitude, longitude] of the maneuver point")


class DrivingRouteResult(BaseModel):
    coordinates: List[List[float]] = Field(..., description="Array of [latitude, longitude] route waypoints along actual streets")
    distance_km: float = Field(..., description="Real street driving distance in kilometers")
    duration_minutes: float = Field(..., description="Estimated travel time in minutes")
    is_real_route: bool = Field(default=True, description="Whether routed via real road network or straight line fallback")
    steps: List[RouteStep] = Field(default_factory=list, description="Turn-by-turn directions, empty if unavailable (e.g. straight-line fallback)")

