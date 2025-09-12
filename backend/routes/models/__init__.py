"""
Routes models package.

This package contains all models for the routes app, split into separate files
for better modularity and maintainability.
"""

from .trip import Trip
from .route import Route
from .waypoint import Waypoint

__all__ = ['Trip', 'Route', 'Waypoint']
