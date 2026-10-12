from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.tomtom import (
    TomTomHistoricalTrafficRequest,
    TomTomHistoricalTrafficResponse,
    TomTomLiveTrafficRequest,
    TomTomLiveTrafficResponse
)
from app.services.tomtom_service import (
    get_tomtom_historical_traffic,
    get_tomtom_live_traffic
)

router = APIRouter(
    prefix="/tomtom",
    tags=["TomTom Traffic Intelligence"]
)


# ============================================================================
# HISTORICAL TRAFFIC ENDPOINTS
# ============================================================================

@router.post(
    "/historical",
    response_model=TomTomHistoricalTrafficResponse,
    summary="Get Historical Traffic Data from TomTom API (POST)"
)
def get_historical_traffic_post(
    req: TomTomHistoricalTrafficRequest,
    db: Session = Depends(get_db)
):
    """
    Query historical traffic flow data from TomTom Routing & Speed Profiles API
    by passing location parameters (start & end location names or coordinates)
    and an optional historical departure timestamp.

    - **start_location**: e.g. "Uppal Main Road, Hyderabad"
    - **end_location**: e.g. "DSL Virtue Mall Uppal, Hyderabad"
    - **start_latitude / start_longitude**: optional explicit GPS coordinates
    - **end_latitude / end_longitude**: optional explicit GPS coordinates
    - **depart_at**: optional ISO-8601 string (e.g. "2024-05-08T09:00:00"). Defaults to 7 days ago if omitted.
    """
    return get_tomtom_historical_traffic(
        start_location=req.start_location,
        end_location=req.end_location,
        start_latitude=req.start_latitude,
        start_longitude=req.start_longitude,
        end_latitude=req.end_latitude,
        end_longitude=req.end_longitude,
        depart_at=req.depart_at,
        db=db
    )


@router.get(
    "/historical",
    response_model=TomTomHistoricalTrafficResponse,
    summary="Get Historical Traffic Data from TomTom API (GET)"
)
def get_historical_traffic_get(
    start_location: Optional[str] = Query(None, description="Start address or landmark (e.g. 'Uppal Main Road, Hyderabad')"),
    end_location: Optional[str] = Query(None, description="End address or landmark (e.g. 'DSL Virtue Mall Uppal, Hyderabad')"),
    start_latitude: Optional[float] = Query(None, description="Start latitude coordinate"),
    start_longitude: Optional[float] = Query(None, description="Start longitude coordinate"),
    end_latitude: Optional[float] = Query(None, description="End latitude coordinate"),
    end_longitude: Optional[float] = Query(None, description="End longitude coordinate"),
    depart_at: Optional[str] = Query(None, description="Historical ISO departure timestamp (e.g. '2024-05-08T09:00:00')"),
    db: Session = Depends(get_db)
):
    """
    Query historical traffic flow data from TomTom Routing & Speed Profiles API via GET query parameters.
    """
    return get_tomtom_historical_traffic(
        start_location=start_location,
        end_location=end_location,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        end_latitude=end_latitude,
        end_longitude=end_longitude,
        depart_at=depart_at,
        db=db
    )


# Alias route for /tomtom/historic
@router.post("/historic", response_model=TomTomHistoricalTrafficResponse, include_in_schema=False)
def get_historic_traffic_alias_post(req: TomTomHistoricalTrafficRequest, db: Session = Depends(get_db)):
    return get_historical_traffic_post(req, db)


@router.get("/historic", response_model=TomTomHistoricalTrafficResponse, include_in_schema=False)
def get_historic_traffic_alias_get(
    start_location: Optional[str] = Query(None),
    end_location: Optional[str] = Query(None),
    start_latitude: Optional[float] = Query(None),
    start_longitude: Optional[float] = Query(None),
    end_latitude: Optional[float] = Query(None),
    end_longitude: Optional[float] = Query(None),
    depart_at: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_historical_traffic_get(
        start_location, end_location, start_latitude, start_longitude, end_latitude, end_longitude, depart_at, db
    )


# ============================================================================
# LIVE TRAFFIC ENDPOINTS
# ============================================================================

@router.post(
    "/live",
    response_model=TomTomLiveTrafficResponse,
    summary="Get Real-Time Live Traffic Data from TomTom API (POST)"
)
def get_live_traffic_post(
    req: TomTomLiveTrafficRequest,
    db: Session = Depends(get_db)
):
    """
    Query real-time live traffic telemetry from TomTom Traffic Flow APIs
    by passing location parameters (start & end route corridor OR single location point).

    - **start_location & end_location**: route corridor addresses or coordinates
    - **location OR latitude & longitude**: single monitored spot / junction
    """
    return get_tomtom_live_traffic(
        start_location=req.start_location,
        end_location=req.end_location,
        start_latitude=req.start_latitude,
        start_longitude=req.start_longitude,
        end_latitude=req.end_latitude,
        end_longitude=req.end_longitude,
        location=req.location,
        latitude=req.latitude,
        longitude=req.longitude,
        db=db
    )


@router.get(
    "/live",
    response_model=TomTomLiveTrafficResponse,
    summary="Get Real-Time Live Traffic Data from TomTom API (GET)"
)
def get_live_traffic_get(
    start_location: Optional[str] = Query(None, description="Origin address or landmark"),
    end_location: Optional[str] = Query(None, description="Destination address or landmark"),
    start_latitude: Optional[float] = Query(None, description="Origin latitude"),
    start_longitude: Optional[float] = Query(None, description="Origin longitude"),
    end_latitude: Optional[float] = Query(None, description="Destination latitude"),
    end_longitude: Optional[float] = Query(None, description="Destination longitude"),
    location: Optional[str] = Query(None, description="Single point address or landmark"),
    latitude: Optional[float] = Query(None, description="Single point latitude"),
    longitude: Optional[float] = Query(None, description="Single point longitude"),
    db: Session = Depends(get_db)
):
    """
    Query real-time live traffic telemetry from TomTom Traffic Flow APIs via GET query parameters.
    """
    return get_tomtom_live_traffic(
        start_location=start_location,
        end_location=end_location,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        end_latitude=end_latitude,
        end_longitude=end_longitude,
        location=location,
        latitude=latitude,
        longitude=longitude,
        db=db
    )
