"""
URL configuration for routes app.

Defines URL patterns for all route-related endpoints including
the main trip calculation endpoint specified in the assessment.
"""

from django.urls import path
from . import views

app_name = "routes"

urlpatterns = [
    # Main assessment endpoint - POST /api/trips/calculate
    path("trips/calculate/", views.TripCalculateView.as_view(), name="trip-calculate"),
    # Trip management endpoints
    path("trips/", views.TripListView.as_view(), name="trip-list"),
    path("trips/<uuid:pk>/", views.TripDetailView.as_view(), name="trip-detail"),
    # Route and logs endpoints - specified in Phase 2
    path(
        "trips/<uuid:trip_id>/route/", views.TripRouteView.as_view(), name="trip-route"
    ),
    path("trips/<uuid:trip_id>/logs/", views.TripLogsView.as_view(), name="trip-logs"),
    # ELD log sheets endpoints
    path("trips/<uuid:trip_id>/log-sheets/", views.TripLogSheetsView.as_view(), name="trip-log-sheets"),
    path("trips/<uuid:trip_id>/log-sheets/<uuid:sheet_id>/grid/", views.trip_log_sheet_grid, name="trip-log-sheet-grid"),
    # API info and health check
    path("", views.api_info, name="api-info"),
    path("health/", views.health_check, name="health-check"),
]
