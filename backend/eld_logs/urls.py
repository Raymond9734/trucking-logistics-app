"""
URL configuration for ELD Logs API endpoints.

Provides URL routing for all ELD logs related endpoints
including daily logs, duty status records, log sheets, and reports.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyLogViewSet,
    ELDLogsGenerationViewSet,
    DutyStatusRecordViewSet,
    LogSheetViewSet,
    ELDComplianceReportViewSet,
    BulkLogOperationViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r"daily-logs", DailyLogViewSet, basename="daily-logs")
router.register(
    r"duty-status-records", DutyStatusRecordViewSet, basename="duty-status-records"
)
router.register(r"log-sheets", LogSheetViewSet, basename="log-sheets")

# Custom URL patterns for non-model viewsets and specific actions
urlpatterns = [
    # Router URLs
    path("", include(router.urls)),
    # ELD Logs Generation endpoints
    path(
        "generate/",
        ELDLogsGenerationViewSet.as_view({"post": "generate"}),
        name="eld-generate-logs",
    ),
    # Duty Status Record endpoints
    path(
        "duty-status/create/",
        DutyStatusRecordViewSet.as_view({"post": "create_status_change"}),
        name="eld-create-status-change",
    ),
    # Log Sheet endpoints
    path(
        "log-sheets/generate/",
        LogSheetViewSet.as_view({"post": "generate"}),
        name="eld-generate-log-sheet",
    ),
    path(
        "log-sheets/<uuid:pk>/grid-data/",
        LogSheetViewSet.as_view({"get": "grid_data"}),
        name="eld-log-sheet-grid-data",
    ),
    # ELD Compliance Reports endpoints
    path(
        "reports/trip/",
        ELDComplianceReportViewSet.as_view({"get": "trip_report"}),
        name="eld-trip-report",
    ),
    # Bulk Operations endpoints
    path(
        "bulk-operations/",
        BulkLogOperationViewSet.as_view({"post": "execute"}),
        name="eld-bulk-operations",
    ),
    # Specific daily log endpoints (alternative to router)
    path(
        "daily-logs/by-trip/",
        DailyLogViewSet.as_view({"get": "by_trip"}),
        name="daily-logs-by-trip",
    ),
    path(
        "daily-logs/<uuid:pk>/certify/",
        DailyLogViewSet.as_view({"post": "certify"}),
        name="daily-logs-certify",
    ),
    path(
        "daily-logs/<uuid:pk>/recalculate-totals/",
        DailyLogViewSet.as_view({"post": "recalculate_totals"}),
        name="daily-logs-recalculate-totals",
    ),
    path(
        "daily-logs/<uuid:pk>/validate-compliance/",
        DailyLogViewSet.as_view({"get": "validate_compliance"}),
        name="daily-logs-validate-compliance",
    ),
]

# URL patterns for API documentation purposes
# eld_patterns = [
#     # GET endpoints
#     path('daily-logs/',
#          'List all daily logs with optional filtering'),
#     path('daily-logs/<uuid:id>/',
#          'Retrieve specific daily log'),
#     path('daily-logs/by-trip/?trip_id=<uuid>',
#          'Get daily logs for specific trip'),
#     path('daily-logs/<uuid:id>/validate-compliance/',
#          'Validate specific daily log compliance'),

#     path('duty-status-records/',
#          'List duty status records with optional filtering'),
#     path('duty-status-records/<uuid:id>/',
#          'Retrieve specific duty status record'),

#     path('log-sheets/',
#          'List log sheets with optional filtering'),
#     path('log-sheets/<uuid:id>/',
#          'Retrieve specific log sheet'),
#     path('log-sheets/<uuid:id>/grid-data/',
#          'Get grid data for visual representation'),

#     path('reports/trip/?trip_id=<uuid>',
#          'Generate comprehensive ELD compliance report'),

#     # POST endpoints
#     path('generate/',
#          'Generate ELD logs for a trip'),
#     path('duty-status/create/',
#          'Create new duty status change record'),
#     path('log-sheets/generate/',
#          'Generate visual log sheet for daily log'),
#     path('bulk-operations/',
#          'Execute bulk operations on multiple logs'),

#     path('daily-logs/',
#          'Create new daily log'),
#     path('daily-logs/<uuid:id>/certify/',
#          'Certify daily log with driver signature'),
#     path('daily-logs/<uuid:id>/recalculate-totals/',
#          'Recalculate total hours for daily log'),

#     # PUT/PATCH endpoints
#     path('daily-logs/<uuid:id>/',
#          'Update specific daily log'),
#     path('duty-status-records/<uuid:id>/',
#          'Update specific duty status record'),
#     path('log-sheets/<uuid:id>/',
#          'Update specific log sheet'),

#     # DELETE endpoints
#     path('daily-logs/<uuid:id>/',
#          'Delete specific daily log'),
#     path('duty-status-records/<uuid:id>/',
#          'Delete specific duty status record'),
#     path('log-sheets/<uuid:id>/',
#          'Delete specific log sheet'),
# ]
