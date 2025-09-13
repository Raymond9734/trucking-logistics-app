"""
Routes serializers package.

This package contains all serializers for the routes app, split into separate files
for better modularity and maintainability.
"""

from .trip_serializer import (
    TripSerializer,
    TripCreateSerializer,
    TripCalculateSerializer,
    TripDetailSerializer,
)
from .route_serializer import RouteSerializer, RouteDetailSerializer
from .waypoint_serializer import WaypointSerializer, WaypointCreateSerializer

__all__ = [
    "TripSerializer",
    "TripCreateSerializer",
    "TripCalculateSerializer",
    "RouteSerializer",
    "RouteDetailSerializer",
    "WaypointSerializer",
    "WaypointCreateSerializer",
    "TripDetailSerializer",
]
