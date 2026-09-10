"""
RoadSense AI - Predictions Modular Router (Backward Compatibility Wrapper)

The predictions functionality has been split into two clearly segregated modules:
1. app.routers.traffic_predictions -> Tag: 'AI Traffic Predictions'
2. app.routers.accident_predictions -> Tag: 'AI Accident Predictions'

This file is maintained so any legacy references continue to work seamlessly.
"""

from fastapi import APIRouter
from app.routers.traffic_predictions import router as traffic_router
from app.routers.accident_predictions import router as accident_router

router = APIRouter()
router.include_router(traffic_router)
router.include_router(accident_router)
