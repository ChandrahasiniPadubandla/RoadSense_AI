from typing import Optional, List
from pydantic import BaseModel, Field


class TomTomLocationPoint(BaseModel):
    name: Optional[str] = Field(None, description="Clean primary name or landmark")
    display_name: Optional[str] = Field(None, description="Full geocoded address or description")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")


class TomTomHistoricalTrafficRequest(BaseModel):
    start_location: Optional[str] = Field(
        None,
        description="Origin address, landmark, or street name (e.g. 'Uppal Main Road, Hyderabad')"
    )
    end_location: Optional[str] = Field(
        None,
        description="Destination address, landmark, or street name (e.g. 'DSL Virtue Mall Uppal, Hyderabad')"
    )
    start_latitude: Optional[float] = Field(None, description="Origin latitude coordinate")
    start_longitude: Optional[float] = Field(None, description="Origin longitude coordinate")
    end_latitude: Optional[float] = Field(None, description="Destination latitude coordinate")
    end_longitude: Optional[float] = Field(None, description="Destination longitude coordinate")
    depart_at: Optional[str] = Field(
        None,
        description="Historical departure time in ISO-8601 format (e.g. '2024-05-08T09:00:00'). Defaults to 7 days ago if omitted."
    )


class TomTomLiveTrafficRequest(BaseModel):
    start_location: Optional[str] = Field(
        None,
        description="Route origin address, landmark, or street name"
    )
    end_location: Optional[str] = Field(
        None,
        description="Route destination address, landmark, or street name"
    )
    start_latitude: Optional[float] = Field(None, description="Route origin latitude")
    start_longitude: Optional[float] = Field(None, description="Route origin longitude")
    end_latitude: Optional[float] = Field(None, description="Route destination latitude")
    end_longitude: Optional[float] = Field(None, description="Route destination longitude")
    location: Optional[str] = Field(
        None,
        description="Single address, corridor, or junction name for spot/segment live telemetry"
    )
    latitude: Optional[float] = Field(None, description="Single point latitude for spot telemetry")
    longitude: Optional[float] = Field(None, description="Single point longitude for spot telemetry")


class TomTomHistoricalTrafficResponse(BaseModel):
    status: str = Field("SUCCESS", description="API status (SUCCESS or ERROR)")
    source: str = Field(
        "TomTom Routing & Historical Speed Profiles API",
        description="Upstream telemetry source"
    )
    query_type: str = Field("historical", description="Query type")
    start_point: TomTomLocationPoint
    end_point: TomTomLocationPoint
    depart_at: str = Field(..., description="Departure ISO timestamp evaluated")
    arrival_at: Optional[str] = Field(None, description="Estimated arrival ISO timestamp")
    distance_meters: int = Field(..., description="Route corridor distance in meters")
    distance_km: float = Field(..., description="Route corridor distance in kilometers")
    travel_time_seconds: int = Field(..., description="Total travel time under historical speed profile")
    travel_time_minutes: float = Field(..., description="Total travel time in minutes")
    historic_traffic_travel_time_seconds: int = Field(
        ...,
        description="Baseline travel time based on TomTom historical Speed Profiles for this day-of-week & hour"
    )
    no_traffic_travel_time_seconds: int = Field(
        ...,
        description="Travel time in uncongested free-flow conditions"
    )
    traffic_delay_seconds: int = Field(..., description="Historical delay relative to free-flow")
    traffic_delay_minutes: float = Field(..., description="Historical delay in minutes")
    average_speed_kmh: float = Field(..., description="Historical average speed in km/h")
    free_flow_speed_kmh: float = Field(..., description="Corridor free-flow speed in km/h")
    slowdown_percentage: float = Field(..., description="Percentage slowdown compared to free-flow")
    congestion_level: str = Field(..., description="Congestion category: LOW | MEDIUM | HIGH | SEVERE")
    traffic_condition: str = Field(..., description="Descriptive traffic flow condition")
    route_points_count: int = Field(..., description="Total GPS coordinate waypoints along corridor")
    sample_waypoints: Optional[List[List[float]]] = Field(
        None,
        description="Sample [[lat, lng], ...] waypoints along corridor"
    )


class TomTomLiveTrafficResponse(BaseModel):
    status: str = Field("SUCCESS", description="API status (SUCCESS or ERROR)")
    source: str = Field(
        "TomTom Real-Time Traffic Flow & Routing API",
        description="Upstream telemetry source"
    )
    query_type: str = Field("live", description="Query type")
    start_point: Optional[TomTomLocationPoint] = None
    end_point: Optional[TomTomLocationPoint] = None
    monitored_point: Optional[TomTomLocationPoint] = None
    depart_at: Optional[str] = None
    arrival_at: Optional[str] = None
    distance_meters: Optional[int] = None
    distance_km: Optional[float] = None
    current_travel_time_seconds: Optional[int] = None
    current_travel_time_minutes: Optional[float] = None
    free_flow_travel_time_seconds: Optional[int] = None
    traffic_delay_seconds: Optional[int] = None
    traffic_delay_minutes: Optional[float] = None
    current_speed_kmh: float = Field(..., description="Real-time observed vehicle speed in km/h")
    free_flow_speed_kmh: float = Field(..., description="Corridor free-flow speed in km/h")
    slowdown_percentage: float = Field(..., description="Percentage slowdown from free-flow")
    congestion_level: str = Field(..., description="Congestion category: LOW | MEDIUM | HIGH | SEVERE")
    traffic_condition: str = Field(..., description="Descriptive traffic status")
    sensor_confidence_score: Optional[float] = Field(
        None,
        description="TomTom sensor confidence percentage (0-100%)"
    )
    road_closure: bool = Field(False, description="Whether corridor segment is marked closed/blocked")
    functional_road_class: Optional[str] = Field(None, description="TomTom Functional Road Class (e.g. FRC1, FRC2)")
    route_points_count: Optional[int] = None
    sample_waypoints: Optional[List[List[float]]] = None
