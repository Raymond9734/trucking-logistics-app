"""
Views for routes app.

Contains API views for trip calculation, route management, and related
endpoints following RESTful patterns.
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Trip
from .serializers import (
    TripSerializer,
    TripCreateSerializer,
    TripCalculateSerializer,
    TripDetailSerializer,
    RouteDetailSerializer,
)
from .services.trip_planner import TripPlannerService
from eld_logs.services import LogSheetRendererService


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class TripCalculateView(APIView):
    """
    POST /api/trips/calculate

    Main endpoint for trip calculation as specified in the assessment.
    Takes trip inputs and returns route instructions and ELD logs.

    Input:
    - current_location: Current driver location
    - pickup_location: Pickup address
    - dropoff_location: Delivery address
    - current_cycle_used: Hours used in current 8-day cycle
    - driver_name: Optional driver name

    Output:
    - Complete trip details with route, waypoints, and ELD log structure
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Calculate trip route and generate ELD logs."""
        try:
            # Transform request data to fit the serializer
            request_data = request.data.copy()
            if 'locations' in request_data:
                locations = request_data.pop('locations')
                if 'current' in locations and locations['current']:
                    request_data['current_location'] = locations['current'].get('displayName', '')
                    if 'coordinates' in locations['current'] and locations['current']['coordinates']:
                        request_data['current_lat'] = locations['current']['coordinates'].get('lat')
                        request_data['current_lng'] = locations['current']['coordinates'].get('lon')
                if 'pickup' in locations and locations['pickup']:
                    request_data['pickup_location'] = locations['pickup'].get('displayName', '')
                    if 'coordinates' in locations['pickup'] and locations['pickup']['coordinates']:
                        request_data['pickup_lat'] = locations['pickup']['coordinates'].get('lat')
                        request_data['pickup_lng'] = locations['pickup']['coordinates'].get('lon')
                if 'dropoff' in locations and locations['dropoff']:
                    request_data['dropoff_location'] = locations['dropoff'].get('displayName', '')
                    if 'coordinates' in locations['dropoff'] and locations['dropoff']['coordinates']:
                        request_data['dropoff_lat'] = locations['dropoff']['coordinates'].get('lat')
                        request_data['dropoff_lng'] = locations['dropoff']['coordinates'].get('lon')

            # Validate input data
            serializer = TripCalculateSerializer(data=request_data)
            if not serializer.is_valid():
                logger.warning(f"Invalid trip calculation input: {serializer.errors}")
                return Response(
                    {"error": "Invalid input data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(f"Request DATA: {request.data}")

            # Extract validated data
            trip_data = serializer.validated_data
            logger.info(
                f"Starting trip calculation for driver: {trip_data.get('driver_name', 'Unknown')}"
            )

            logger.info(f"Serialized Trip DATA: {trip_data}")

            # Calculate route and generate ELD logs using TripPlannerService
            trip_planner = TripPlannerService()
            trip_result = trip_planner.plan_complete_trip(trip_data)

            # Extract trip from result
            trip = trip_result["trip"]

            # Format response using serializer
            response_serializer = TripCalculateSerializer(trip)
            response_data = response_serializer.to_representation(trip)

            # Add comprehensive trip planning results
            response_data.update(
                {
                    "compliance": trip_result["compliance"],
                    "timeline": trip_result["timeline"],
                    "summary": trip_result["summary"],
                    "eld_logs_count": len(trip_result["eld_logs"]),
                }
            )

            # Add ELD logs information
            if hasattr(trip, "daily_logs"):
                logs = trip.daily_logs.all().order_by("log_date")
                response_data["logs"] = [
                    {
                        "log_id": str(log.id),
                        "log_date": log.log_date.isoformat(),
                        "driver_name": log.driver_name,
                        "vehicle_number": log.vehicle_number,
                        "total_miles": (
                            float(log.total_miles_driving_today)
                            if log.total_miles_driving_today
                            else 0
                        ),
                        "duty_status_changes_count": log.duty_status_records.count(),
                        "url": f"/api/trips/{trip.id}/logs/{log.id}/",
                    }
                    for log in logs
                ]

            logger.info(f"Successfully calculated trip {trip.id}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Trip calculation failed: {str(e)}")
            return Response(
                {"error": "Trip calculation failed", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripDetailView(generics.RetrieveAPIView):
    """
    GET /api/trips/{id}/

    Get detailed information about a specific trip including
    route, HOS status, and logs summary.
    """

    queryset = Trip.objects.all()
    serializer_class = TripDetailSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        """Get trip details with related information."""
        try:
            trip = self.get_object()
            serializer = self.get_serializer(trip)

            logger.info(f"Retrieved trip details for {trip.id}")
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Failed to retrieve trip details: {str(e)}")
            return Response(
                {"error": "Failed to retrieve trip", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripRouteView(APIView):
    """
    GET /api/trips/{id}/route

    Get detailed route information for a specific trip including
    waypoints, stops, and route geometry.
    """

    permission_classes = [AllowAny]

    def get(self, request, trip_id):
        """Get detailed route information."""
        try:
            trip = get_object_or_404(Trip, id=trip_id)

            if not hasattr(trip, "route"):
                return Response(
                    {
                        "error": "Route not found",
                        "message": "No route calculated for this trip",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            route = trip.route
            serializer = RouteDetailSerializer(route)

            logger.info(f"Retrieved route details for trip {trip.id}")
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Failed to retrieve route: {str(e)}")
            return Response(
                {"error": "Failed to retrieve route", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripLogsView(APIView):
    """
    GET /api/trips/{id}/logs

    Get ELD logs for a specific trip. Returns daily log sheets
    that can be used for compliance and filled out by drivers.
    """

    permission_classes = [AllowAny]

    def get(self, request, trip_id):
        """Get ELD logs for trip."""
        try:
            trip = get_object_or_404(Trip, id=trip_id)

            # Get all daily logs for this trip
            daily_logs = trip.daily_logs.all().order_by("log_date")

            if not daily_logs.exists():
                return Response(
                    {
                        "error": "No logs found",
                        "message": "No ELD logs generated for this trip",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Format logs response
            logs_data = []
            for log in daily_logs:
                # Get duty status records for this log
                duty_records = log.duty_status_records.all().order_by("start_time")

                log_data = {
                    "log_id": str(log.id),
                    "log_date": log.log_date.isoformat(),
                    "driver_name": log.driver_name,
                    "carrier_name": log.carrier_name,
                    "vehicle_number": log.vehicle_number,
                    "total_miles": (
                        float(log.total_miles_driving_today)
                        if log.total_miles_driving_today
                        else 0
                    ),
                    "duty_status_records": [
                        {
                            "duty_status": record.duty_status,
                            "start_time": (
                                record.start_time.strftime("%H:%M")
                                if record.start_time
                                else None
                            ),
                            "end_time": (
                                record.end_time.strftime("%H:%M")
                                if record.end_time
                                else None
                            ),
                            "duration_hours": (
                                float(record.duration_hours)
                                if record.duration_hours
                                else 0
                            ),
                            "location": record.location or "",
                            "remarks": record.remarks or "",
                        }
                        for record in duty_records
                    ],
                    "summary": {
                        "total_on_duty_hours": float(
                            log.total_hours_on_duty_not_driving
                            + log.total_hours_driving
                        ),
                        "total_driving_hours": float(log.total_hours_driving),
                        "total_off_duty_hours": float(log.total_hours_off_duty),
                        "sleeper_berth_hours": float(log.total_hours_sleeper_berth),
                        "violations": (
                            log.validate_compliance()
                            if hasattr(log, "validate_compliance")
                            else []
                        ),
                    },
                }

                logs_data.append(log_data)

            response_data = {
                "trip_id": str(trip.id),
                "driver_name": trip.driver_name,
                "total_logs": len(logs_data),
                "logs": logs_data,
            }

            logger.info(f"Retrieved {len(logs_data)} ELD logs for trip {trip.id}")
            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to retrieve logs: {str(e)}")
            return Response(
                {"error": "Failed to retrieve logs", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TripListView(generics.ListCreateAPIView):
    """
    GET /api/trips/ - List all trips
    POST /api/trips/ - Create a new trip

    Supporting endpoints for trip management.
    """

    queryset = Trip.objects.all().order_by("-created_at")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.request.method == "POST":
            return TripCreateSerializer
        return TripSerializer

    def perform_create(self, serializer):
        """Create trip with additional processing."""
        trip = serializer.save()
        logger.info(f"Created new trip {trip.id} for driver {trip.driver_name}")


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/health/

    Simple health check endpoint for monitoring.
    """
    return Response(
        {"status": "healthy", "message": "Trucking Logistics API is running"}
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    """
    GET /api/

    API information and available endpoints.
    """
    return Response(
        {
            "name": "Trucking Logistics API",
            "version": "1.0.0",
            "description": "ELD compliance and route planning API for commercial trucking",
            "endpoints": {
                "trip_calculation": "/api/trips/calculate/",
                "trips": "/api/trips/",
                "trip_details": "/api/trips/{id}/",
                "trip_route": "/api/trips/{id}/route/",
                "trip_logs": "/api/trips/{id}/logs/",
                "trip_log_sheets": "/api/trips/{id}/log-sheets/",
                "health": "/api/health/",
            },
            "documentation": {
                "assessment_requirements": {
                    "inputs": [
                        "current_location",
                        "pickup_location",
                        "dropoff_location",
                        "current_cycle_used",
                    ],
                    "outputs": ["route_with_stops", "daily_log_sheets"],
                    "assumptions": [
                        "70hrs_8days",
                        "fuel_every_1000_miles",
                        "1hr_pickup_dropoff",
                    ],
                }
            },
        }
    )


class TripLogSheetsView(APIView):
    """
    GET /api/trips/{id}/log-sheets/
    POST /api/trips/{id}/log-sheets/

    Generate and view ELD log sheets for a trip.
    """

    permission_classes = [AllowAny]

    def get(self, request, trip_id):
        """Get rendered log sheets for a trip."""
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            log_renderer = LogSheetRendererService()

            # Create log sheets for all daily logs
            log_sheets = log_renderer.create_log_sheets_for_trip(trip)

            sheets_data = []
            for sheet in log_sheets:
                sheet_data = {
                    "log_sheet_id": str(sheet.id),
                    "daily_log_id": str(sheet.daily_log.id),
                    "log_date": sheet.daily_log.log_date.isoformat(),
                    "driver_name": sheet.daily_log.driver_name,
                    "is_compliant": sheet.is_compliant,
                    "compliance_score": sheet.compliance_score,
                    "compliance_issues": sheet.compliance_issues,
                    "has_grid_data": bool(sheet.grid_data),
                    "pdf_available": sheet.pdf_generated,
                    "visual_grid_url": f"/api/trips/{trip_id}/log-sheets/{sheet.id}/grid/",
                }
                sheets_data.append(sheet_data)

            response_data = {
                "trip_id": str(trip.id),
                "driver_name": trip.driver_name,
                "total_log_sheets": len(sheets_data),
                "log_sheets": sheets_data,
            }

            logger.info(f"Retrieved {len(sheets_data)} log sheets for trip {trip.id}")
            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to retrieve log sheets: {str(e)}")
            return Response(
                {"error": "Failed to retrieve log sheets", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, trip_id):
        """Generate new log sheets for a trip."""
        try:
            trip = get_object_or_404(Trip, id=trip_id)

            # Check if trip has daily logs
            if not hasattr(trip, "daily_logs") or not trip.daily_logs.exists():
                # Generate daily logs first using TripPlannerService
                trip_planner = TripPlannerService()
                if trip_planner.eld_generator:
                    daily_logs = trip_planner.eld_generator.generate_trip_daily_logs(
                        trip
                    )
                    logger.info(
                        f"Generated {len(daily_logs)} daily logs for trip {trip.id}"
                    )
                else:
                    return Response(
                        {"error": "ELD service not available"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

            # Generate log sheets
            log_renderer = LogSheetRendererService()
            log_sheets = log_renderer.create_log_sheets_for_trip(trip)

            response_data = {
                "message": "Log sheets generated successfully",
                "trip_id": str(trip.id),
                "log_sheets_generated": len(log_sheets),
                "log_sheets": [
                    {
                        "log_sheet_id": str(sheet.id),
                        "log_date": sheet.daily_log.log_date.isoformat(),
                        "is_compliant": sheet.is_compliant,
                        "compliance_score": sheet.compliance_score,
                    }
                    for sheet in log_sheets
                ],
            }

            logger.info(f"Generated {len(log_sheets)} log sheets for trip {trip.id}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to generate log sheets: {str(e)}")
            return Response(
                {"error": "Failed to generate log sheets", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["GET"])
@permission_classes([AllowAny])
def trip_log_sheet_grid(request, trip_id, sheet_id):
    """
    GET /api/trips/{trip_id}/log-sheets/{sheet_id}/grid/

    Get HTML visual representation of a specific log sheet grid.
    """
    try:
        from eld_logs.models import LogSheet

        trip = get_object_or_404(Trip, id=trip_id)
        log_sheet = get_object_or_404(LogSheet, id=sheet_id, daily_log__trip=trip)

        log_renderer = LogSheetRendererService()
        html_grid = log_renderer.render_html_grid(log_sheet)

        # Return HTML content
        from django.http import HttpResponse

        return HttpResponse(html_grid, content_type="text/html")

    except Exception as e:
        logger.error(f"Failed to render log sheet grid: {str(e)}")
        return Response(
            {"error": "Failed to render grid", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
