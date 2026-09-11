from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class GeocodeSearchResult(BaseModel):
    display_name: str = Field(..., description="Full formatted address/name from OpenStreetMap")
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    type: Optional[str] = Field(default="location", description="Type of place (e.g. suburb, road, amenity)")
    importance: Optional[float] = Field(default=0.0, description="Relevance score")
    address: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Address breakdown")


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
