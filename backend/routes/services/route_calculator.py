"""
Route Calculator Service for routes app.

Contains the main business logic for calculating routes, determining stops,
and creating route plans with HOS compliance.
"""

import logging
import json
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import Trip, Route, Waypoint
from hos_compliance.models import HOSStatus, RestBreak
from .mapping_service import MappingService
from common.validators import (
    get_fuel_stop_interval_miles,
    get_pickup_dropoff_duration_hours,
)

logger = logging.getLogger(__name__)


class RouteCalculatorService:
    """
    Service class for calculating routes and managing trip planning.

    This service encapsulates all the business logic for:
    - Route calculation using mapping APIs
    - HOS compliance checking and break scheduling
    - Waypoint creation and sequencing
    - ELD log planning

    Single Responsibility: Route calculation and trip planning logic
    """

    def __init__(self):
        """Initialize the route calculator service."""
        self.mapping_service = MappingService()
        self.fuel_interval_miles = get_fuel_stop_interval_miles()  # 1000 miles
        self.pickup_dropoff_duration_hours = (
            get_pickup_dropoff_duration_hours()
        )  # 1 hour

    def calculate_trip_route(self, trip_data):
        """
        Calculate complete route for a trip including HOS compliance.

        This is the main method called by the API endpoint.

        Args:
            trip_data (dict): Trip input data from API

        Returns:
            Trip: Calculated trip with route, waypoints, and HOS status

        Raises:
            ValueError: If input data is invalid
            Exception: If route calculation fails
        """
        try:
            with transaction.atomic():
                # Step 1: Create or get trip record
                trip = self._create_trip_from_data(trip_data)

                # Step 2: Calculate route using mapping service
                route_info = self._calculate_base_route(trip)

                # Step 3: Create route record
                route = self._create_route_record(trip, route_info)

                # Step 4: Plan waypoints with HOS compliance
                waypoints = self._plan_route_waypoints(route, trip)

                # Step 5: Create HOS status
                hos_status = self._create_hos_status(trip)

                # Step 6: Plan required rest breaks
                rest_breaks = self._plan_rest_breaks(trip, route)

                # Step 8: Update trip with calculated results
                self._finalize_trip_calculation(trip, route)

                logger.info(f"Successfully calculated route for trip {trip.id}")
                return trip

        except Exception as e:
            logger.error(f"Route calculation failed: {str(e)}")
            raise

    def _create_trip_from_data(self, trip_data):
        """Create trip record from input data."""
        trip = Trip.objects.create(
            driver_name=trip_data.get("driver_name", "Driver"),
            current_location=trip_data["current_location"],
            current_lat=trip_data.get("current_lat"),
            current_lng=trip_data.get("current_lng"),
            pickup_location=trip_data["pickup_location"],
            pickup_lat=trip_data.get("pickup_lat"),
            pickup_lng=trip_data.get("pickup_lng"),
            dropoff_location=trip_data["dropoff_location"],
            dropoff_lat=trip_data.get("dropoff_lat"),
            dropoff_lng=trip_data.get("dropoff_lng"),
            current_cycle_used=trip_data["current_cycle_used"],
            status=Trip.StatusChoices.PLANNED,
        )

        logger.info(f"Created trip {trip.id} for driver {trip.driver_name}")
        return trip

    def _calculate_base_route(self, trip):
        """Calculate base route using mapping service."""
        locations = []
        if trip.current_lat and trip.current_lng and trip.pickup_lat and trip.pickup_lng and trip.dropoff_lat and trip.dropoff_lng:
            locations = [
                {"lat": trip.current_lat, "lng": trip.current_lng},
                {"lat": trip.pickup_lat, "lng": trip.pickup_lng},
                {"lat": trip.dropoff_lat, "lng": trip.dropoff_lng},
            ]
        else:
            locations = [trip.current_location, trip.pickup_location, trip.dropoff_location]

        route_info = self.mapping_service.calculate_route(locations)

        # Add coordinates to trip if returned by mapping service and not already present
        if not (trip.current_lat and trip.current_lng) and route_info.get("coordinates"):
            coords = route_info["coordinates"]
            if len(coords) >= 3:
                trip.current_lat = coords[0]["lat"]
                trip.current_lng = coords[0]["lng"]
                trip.pickup_lat = coords[1]["lat"]
                trip.pickup_lng = coords[1]["lng"]
                trip.dropoff_lat = coords[2]["lat"]
                trip.dropoff_lng = coords[2]["lng"]
                trip.save()

        return route_info

    def _create_route_record(self, trip, route_info):
        """Create route database record."""
        # Ensure geometry is stored as JSON string
        geometry = route_info.get("geometry", "")
        if geometry and not isinstance(geometry, str):
            geometry = json.dumps(geometry)
        
        route = Route.objects.create(
            trip=trip,
            total_distance_miles=Decimal(str(route_info["distance_miles"])),
            estimated_driving_time_minutes=route_info["duration_minutes"],
            route_geometry=geometry,
            mapping_service=route_info.get("service", "openrouteservice"),
            traffic_considered=route_info.get("traffic_considered", False),
            route_profile="driving-hgv",
            is_fastest_route=True,
        )

        logger.info(
            f"Created route {route.id} for trip {trip.id}: {route.total_distance_miles} miles"
        )
        return route

    def _plan_route_waypoints(self, route, trip):
        """Plan all waypoints including mandatory stops."""
        waypoints = []
        sequence = 0
        cumulative_distance = Decimal("0")
        cumulative_time_minutes = 0

        # Origin waypoint (current location)
        waypoints.append(
            self._create_waypoint(
                route,
                sequence,
                trip.current_location,
                trip.current_lat,
                trip.current_lng,
                Waypoint.WaypointType.ORIGIN,
                0,
                0,
                0,
                "",
            )
        )
        sequence += 1

        # Calculate distance segments
        total_distance = float(route.total_distance_miles)
        total_time = route.estimated_driving_time_minutes

        # Pickup waypoint
        pickup_distance = total_distance * 0.3  # Assume pickup is 30% of total route
        pickup_time = int(total_time * 0.3)
        waypoints.append(
            self._create_waypoint(
                route,
                sequence,
                trip.pickup_location,
                trip.pickup_lat,
                trip.pickup_lng,
                Waypoint.WaypointType.PICKUP,
                pickup_distance,
                pickup_time,
                int(self.pickup_dropoff_duration_hours * 60),
                "Pickup cargo",
            )
        )
        cumulative_distance += Decimal(str(pickup_distance))
        cumulative_time_minutes += pickup_time + int(
            self.pickup_dropoff_duration_hours * 60
        )
        sequence += 1

        # Plan fuel stops based on distance
        fuel_stops_needed = int(total_distance // self.fuel_interval_miles)
        for i in range(fuel_stops_needed):
            fuel_distance = self.fuel_interval_miles
            fuel_time = int((fuel_distance / total_distance) * total_time)

            waypoints.append(
                self._create_waypoint(
                    route,
                    sequence,
                    f"Fuel Stop #{i+1}",
                    None,
                    None,
                    Waypoint.WaypointType.FUEL_STOP,
                    fuel_distance,
                    fuel_time,
                    30,
                    "Fuel stop",
                )
            )
            sequence += 1

        # Plan HOS rest stops
        hos_stops = self._calculate_hos_stops(route, trip)
        for stop in hos_stops:
            waypoints.append(
                self._create_waypoint(
                    route,
                    sequence,
                    stop["location"],
                    None,
                    None,
                    stop["type"],
                    stop["distance"],
                    stop["time"],
                    stop["duration"],
                    stop["reason"],
                )
            )
            sequence += 1

        # Dropoff waypoint
        remaining_distance = total_distance - pickup_distance
        remaining_time = total_time - pickup_time
        waypoints.append(
            self._create_waypoint(
                route,
                sequence,
                trip.dropoff_location,
                trip.dropoff_lat,
                trip.dropoff_lng,
                Waypoint.WaypointType.DROPOFF,
                remaining_distance,
                remaining_time,
                int(self.pickup_dropoff_duration_hours * 60),
                "Deliver cargo",
            )
        )

        return waypoints

    def _create_waypoint(
        self,
        route,
        sequence,
        address,
        lat,
        lng,
        waypoint_type,
        distance,
        time_minutes,
        stop_duration,
        reason,
    ):
        """Helper method to create waypoint records."""
        waypoint = Waypoint.objects.create(
            route=route,
            sequence_order=sequence,
            latitude=lat or Decimal("0"),
            longitude=lng or Decimal("0"),
            address=address,
            waypoint_type=waypoint_type,
            distance_from_previous_miles=Decimal(str(distance)),
            estimated_time_from_previous_minutes=time_minutes,
            is_mandatory_stop=waypoint_type
            in [
                Waypoint.WaypointType.PICKUP,
                Waypoint.WaypointType.DROPOFF,
                Waypoint.WaypointType.FUEL_STOP,
                Waypoint.WaypointType.REST_STOP,
                Waypoint.WaypointType.BREAK_30MIN,
                Waypoint.WaypointType.BREAK_10HOUR,
            ],
            estimated_stop_duration_minutes=stop_duration,
            stop_reason=reason,
        )
        return waypoint

    def _calculate_hos_stops(self, route, trip):
        """Calculate required HOS rest stops."""
        stops = []
        total_distance = float(route.total_distance_miles)
        total_time_hours = route.estimated_driving_time_minutes / 60
        current_cycle_hours = float(trip.current_cycle_used)

        # Calculate if 30-minute break is needed
        if total_time_hours > 8:
            stops.append(
                {
                    "location": "Rest Area - 30 Min Break",
                    "type": Waypoint.WaypointType.BREAK_30MIN,
                    "distance": total_distance * 0.6,  # 60% through route
                    "time": int(route.estimated_driving_time_minutes * 0.6),
                    "duration": 30,
                    "reason": "30-minute break after 8 hours driving",
                }
            )

        # Calculate if 10-hour break is needed
        if total_time_hours > 10 or (current_cycle_hours + total_time_hours) > 60:
            stops.append(
                {
                    "location": "Truck Stop - 10 Hour Rest",
                    "type": Waypoint.WaypointType.BREAK_10HOUR,
                    "distance": total_distance * 0.8,  # 80% through route
                    "time": int(route.estimated_driving_time_minutes * 0.8),
                    "duration": 600,  # 10 hours
                    "reason": "10-hour rest break required",
                }
            )

        return stops

    def _create_hos_status(self, trip):
        """Create HOS status record for trip."""
        # Calculate available hours before creating the object
        current_cycle_hours = trip.current_cycle_used
        available_cycle_hours = max(Decimal("0"), Decimal("70") - current_cycle_hours)

        hos_status = HOSStatus.objects.create(
            trip=trip,
            current_cycle_hours=current_cycle_hours,
            available_cycle_hours=available_cycle_hours,
            current_duty_period_hours=Decimal("0"),
            available_duty_period_hours=Decimal("14"),
            current_driving_hours=Decimal("0"),
            available_driving_hours=Decimal("11"),
            hours_since_last_break=Decimal("0"),
            current_duty_status=HOSStatus.DutyStatus.OFF_DUTY,
        )

        # Recalculate to ensure all compliance flags are set correctly
        hos_status.calculate_available_hours()

        logger.info(f"Created HOS status for trip {trip.id}")
        return hos_status

    def _plan_rest_breaks(self, trip, route):
        """Plan required rest breaks based on route and HOS."""
        breaks = []
        driving_time_hours = route.estimated_driving_time_minutes / 60

        # 30-minute break after 8 hours
        if driving_time_hours >= 8:
            breaks.append(
                RestBreak.objects.create(
                    trip=trip,
                    break_type=RestBreak.BreakType.THIRTY_MINUTE,
                    duration_hours=Decimal("0.5"),
                    required_at_driving_hours=Decimal("8"),
                    location_description="Rest area or truck stop",
                    is_mandatory=True,
                    regulation_reference="395.3(a)(3)(ii)",
                )
            )

        # 10-hour break if route exceeds daily driving limit
        if driving_time_hours >= 11:
            breaks.append(
                RestBreak.objects.create(
                    trip=trip,
                    break_type=RestBreak.BreakType.TEN_HOUR,
                    duration_hours=Decimal("10"),
                    required_at_driving_hours=Decimal("11"),
                    location_description="Truck stop with parking",
                    is_mandatory=True,
                    regulation_reference="395.3(a)(1)",
                )
            )

        return breaks

    def _finalize_trip_calculation(self, trip, route):
        """Update trip with final calculated results."""
        trip.total_distance_miles = route.total_distance_miles
        trip.estimated_driving_time_hours = Decimal(
            str(route.estimated_driving_time_hours)
        )
        trip.save()

        logger.info(f"Finalized trip calculation for {trip.id}")

    def recalculate_route(self, trip):
        """Recalculate route for existing trip."""
        # Delete existing route and related data
        if hasattr(trip, "route"):
            trip.route.delete()

        # Recalculate using existing trip data
        trip_data = {
            "driver_name": trip.driver_name,
            "current_location": trip.current_location,
            "pickup_location": trip.pickup_location,
            "dropoff_location": trip.dropoff_location,
            "current_cycle_used": trip.current_cycle_used,
        }

        return self.calculate_trip_route(trip_data)

    def get_route_alternatives(self, trip, count=3):
        """Get alternative routes for a trip."""
        # This would integrate with mapping service to get alternative routes
        # For now, return single route with variations
        base_route = trip.route if hasattr(trip, "route") else None
        if not base_route:
            return []

        alternatives = []
        # Implementation would call mapping service for alternatives
        # This is a placeholder for the service structure

        return alternatives
