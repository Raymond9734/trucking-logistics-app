"""
Trip Planner Service for comprehensive trip planning.

Coordinates between route calculation, HOS compliance, and ELD logging
to provide complete trip planning functionality.
"""

import logging
from django.db import transaction
from django.utils import timezone
from ..models import Trip
from .route_calculator import RouteCalculatorService
from eld_logs.services import DailyLogGeneratorService

logger = logging.getLogger(__name__)


class TripPlannerService:
    """
    High-level service for comprehensive trip planning.

    Coordinates between route calculation, HOS compliance checking,
    and ELD log generation to provide complete trip planning.

    Single Responsibility: Trip planning orchestration
    """

    def __init__(self):
        """Initialize trip planner with required services."""
        self.route_calculator = RouteCalculatorService()
        # Initialize ELD service now that it's implemented
        try:
            self.eld_generator = DailyLogGeneratorService()
        except ImportError as e:
            logger.warning(f"ELD service not available: {e}")
            self.eld_generator = None

    def plan_complete_trip(self, trip_data):
        """
        Plan a complete trip with route, HOS compliance, and ELD logs.

        This is the main entry point for the trip calculation API endpoint.

        Args:
            trip_data (dict): Trip input data from API

        Returns:
            dict: Complete trip plan with all components
        """
        try:
            with transaction.atomic():
                # Step 1: Calculate route
                trip = self.route_calculator.calculate_trip_route(trip_data)

                # Step 2: Validate HOS compliance
                compliance_info = self._validate_trip_compliance(trip)

                # Step 3: Generate trip timeline
                timeline = self._generate_trip_timeline(trip)

                # Step 4: Generate ELD logs if generator is available
                eld_logs = []
                if self.eld_generator:
                    try:
                        eld_logs = self.eld_generator.generate_trip_daily_logs(trip)
                        logger.info(
                            f"Generated {len(eld_logs)} ELD logs for trip {trip.id}"
                        )
                    except Exception as e:
                        logger.warning(f"ELD log generation failed: {str(e)}")
                        # Continue without ELD logs if generation fails

                # Step 5: Create trip summary
                summary = self._create_trip_summary(trip, compliance_info, timeline)
                summary["eld_logs_generated"] = len(eld_logs)

                logger.info(f"Successfully planned complete trip {trip.id}")

                return {
                    "trip": trip,
                    "compliance": compliance_info,
                    "timeline": timeline,
                    "eld_logs": eld_logs,
                    "summary": summary,
                }

        except Exception as e:
            logger.error(f"Trip planning failed: {str(e)}")
            raise

    def _validate_trip_compliance(self, trip):
        """Validate trip against HOS regulations."""
        try:
            hos_status = trip.hos_status
            route = trip.route

            # Calculate total trip time including stops
            total_time_hours = route.total_time_with_stops_hours
            driving_time_hours = route.estimated_driving_time_hours

            # Check various compliance scenarios
            compliance_issues = []
            compliance_warnings = []

            # Check if trip can be completed in current cycle
            available_hours = float(hos_status.available_cycle_hours)
            if total_time_hours > available_hours:
                compliance_issues.append(
                    {
                        "type": "cycle_limit",
                        "message": f"Trip requires {total_time_hours}h but only {available_hours}h available in cycle",
                        "severity": "blocking",
                    }
                )

            # Check if trip requires multi-day driving
            if driving_time_hours > 11:
                compliance_warnings.append(
                    {
                        "type": "multi_day_driving",
                        "message": f"Trip requires {driving_time_hours}h driving (>11h limit), will need overnight rest",
                        "severity": "info",
                    }
                )

            # Check if 30-minute break is needed
            if driving_time_hours > 8:
                compliance_warnings.append(
                    {
                        "type": "30_minute_break",
                        "message": "30-minute break required after 8 hours of driving",
                        "severity": "required",
                    }
                )

            return {
                "is_compliant": len(compliance_issues) == 0,
                "can_start_immediately": hos_status.can_drive,
                "issues": compliance_issues,
                "warnings": compliance_warnings,
                "hos_status": {
                    "available_cycle_hours": available_hours,
                    "available_driving_hours": float(
                        hos_status.available_driving_hours
                    ),
                    "needs_30_minute_break": hos_status.needs_30_minute_break,
                    "violation_reason": hos_status.violation_reason,
                },
            }

        except Exception as e:
            logger.error(f"Compliance validation failed: {str(e)}")
            return {
                "is_compliant": False,
                "can_start_immediately": False,
                "issues": [
                    {
                        "type": "validation_error",
                        "message": "Could not validate compliance",
                    }
                ],
                "warnings": [],
                "hos_status": None,
            }

    def _generate_trip_timeline(self, trip):
        """Generate detailed trip timeline with stops and breaks."""
        try:
            route = trip.route
            waypoints = route.waypoints.all().order_by("sequence_order")

            timeline = []
            current_time = timezone.now()

            for waypoint in waypoints:
                # Add travel segment
                if waypoint.estimated_time_from_previous_minutes > 0:
                    timeline.append(
                        {
                            "type": "driving",
                            "start_time": current_time.isoformat(),
                            "duration_minutes": waypoint.estimated_time_from_previous_minutes,
                            "distance_miles": float(
                                waypoint.distance_from_previous_miles
                            ),
                            "description": f"Drive to {waypoint.get_stop_type_display_name()}",
                        }
                    )
                    current_time += timezone.timedelta(
                        minutes=waypoint.estimated_time_from_previous_minutes
                    )

                # Add stop/waypoint
                if waypoint.estimated_stop_duration_minutes > 0:
                    timeline.append(
                        {
                            "type": "stop",
                            "waypoint_type": waypoint.waypoint_type,
                            "location": waypoint.address,
                            "start_time": current_time.isoformat(),
                            "duration_minutes": waypoint.estimated_stop_duration_minutes,
                            "reason": waypoint.stop_reason,
                            "is_mandatory": waypoint.is_mandatory_stop,
                        }
                    )
                    current_time += timezone.timedelta(
                        minutes=waypoint.estimated_stop_duration_minutes
                    )

            # Add rest breaks from compliance planning
            rest_breaks = trip.rest_breaks.all().order_by("required_at_driving_hours")
            for break_obj in rest_breaks:
                timeline.append(
                    {
                        "type": "rest_break",
                        "break_type": break_obj.break_type,
                        "duration_hours": float(break_obj.duration_hours),
                        "reason": break_obj.get_regulation_description(),
                        "is_mandatory": break_obj.is_mandatory,
                        "estimated_time": current_time.isoformat(),
                    }
                )

            return {
                "total_timeline_hours": (current_time - timezone.now()).total_seconds()
                / 3600,
                "estimated_completion": current_time.isoformat(),
                "events": timeline,
                "summary": {
                    "driving_segments": len(
                        [e for e in timeline if e["type"] == "driving"]
                    ),
                    "stops": len([e for e in timeline if e["type"] == "stop"]),
                    "rest_breaks": len(
                        [e for e in timeline if e["type"] == "rest_break"]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Timeline generation failed: {str(e)}")
            return {
                "total_timeline_hours": 0,
                "estimated_completion": timezone.now().isoformat(),
                "events": [],
                "summary": {"driving_segments": 0, "stops": 0, "rest_breaks": 0},
            }

    def _create_trip_summary(self, trip, compliance_info, timeline):
        """Create comprehensive trip summary."""
        route = trip.route

        return {
            "trip_id": str(trip.id),
            "driver_name": trip.driver_name,
            "status": trip.status,
            "route_summary": {
                "total_distance_miles": float(route.total_distance_miles),
                "estimated_driving_time_hours": route.estimated_driving_time_hours,
                "total_time_with_stops_hours": route.total_time_with_stops_hours,
                "average_speed_mph": route.average_speed_mph,
                "waypoints_count": route.waypoints.count(),
                "mandatory_stops_count": route.waypoints.filter(
                    is_mandatory_stop=True
                ).count(),
            },
            "hos_impact": {
                "cycle_hours_used": float(trip.current_cycle_used),
                "additional_hours_required": timeline["total_timeline_hours"],
                "cycle_hours_after_trip": float(trip.current_cycle_used)
                + timeline["total_timeline_hours"],
                "compliance_status": compliance_info["is_compliant"],
                "can_start_immediately": compliance_info["can_start_immediately"],
            },
            "timeline_summary": timeline["summary"],
            "estimated_completion": timeline["estimated_completion"],
            "next_steps": self._get_next_steps(trip, compliance_info),
        }

    def _get_next_steps(self, trip, compliance_info):
        """Determine next steps for trip execution."""
        next_steps = []

        if not compliance_info["can_start_immediately"]:
            next_steps.append(
                {
                    "action": "resolve_hos_violation",
                    "description": compliance_info["hos_status"]["violation_reason"],
                    "priority": "high",
                }
            )

        if compliance_info["warnings"]:
            for warning in compliance_info["warnings"]:
                if warning["severity"] == "required":
                    next_steps.append(
                        {
                            "action": "plan_break",
                            "description": warning["message"],
                            "priority": "medium",
                        }
                    )

        if not next_steps:
            next_steps.append(
                {
                    "action": "start_trip",
                    "description": "Trip is ready to begin",
                    "priority": "normal",
                }
            )

        return next_steps

    def update_trip_progress(self, trip_id, current_location, odometer_reading=None):
        """Update trip progress and recalculate remaining route."""
        try:
            trip = Trip.objects.get(id=trip_id)

            # Update current location
            trip.current_location = current_location
            trip.save()

            # Recalculate remaining route if trip is in progress
            if trip.status == Trip.StatusChoices.IN_PROGRESS:
                # This would recalculate the route from current position
                # Implementation depends on specific requirements
                pass

            logger.info(f"Updated progress for trip {trip_id}")
            return trip

        except Trip.DoesNotExist:
            logger.error(f"Trip {trip_id} not found")
            raise
        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")
            raise

    def cancel_trip(self, trip_id, reason=""):
        """Cancel a planned trip."""
        try:
            trip = Trip.objects.get(id=trip_id)

            if trip.status not in [
                Trip.StatusChoices.PLANNED,
                Trip.StatusChoices.IN_PROGRESS,
            ]:
                raise ValueError(f"Cannot cancel trip with status {trip.status}")

            trip.status = Trip.StatusChoices.CANCELLED
            trip.save()

            # Could add cancellation reason to a separate model if needed
            logger.info(f"Cancelled trip {trip_id}: {reason}")
            return trip

        except Trip.DoesNotExist:
            logger.error(f"Trip {trip_id} not found")
            raise
        except Exception as e:
            logger.error(f"Trip cancellation failed: {str(e)}")
            raise

    def get_trip_alternatives(self, trip_id, alternative_count=3):
        """Get alternative route options for a trip."""
        try:
            trip = Trip.objects.get(id=trip_id)
            alternatives = self.route_calculator.get_route_alternatives(
                trip, alternative_count
            )

            return alternatives

        except Trip.DoesNotExist:
            logger.error(f"Trip {trip_id} not found")
            raise
        except Exception as e:
            logger.error(f"Alternative generation failed: {str(e)}")
            raise
