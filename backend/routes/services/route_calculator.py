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
from .overpass_service import OverpassService
from ..models.osm_location_cache import OSMLocationCache
from common.validators import (
    get_fuel_stop_interval_miles,
    get_pickup_dropoff_duration_hours,
    calculate_distance_miles,
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
        self.overpass_service = OverpassService()
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
                
                # Step 3.5: Cache OSM amenities along route
                self._cache_osm_amenities_for_route(route, route_info)

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
    
    def _cache_osm_amenities_for_route(self, route, route_info):
        """Cache OSM amenities along the route corridor."""
        try:
            # Extract route coordinates from geometry
            route_coordinates = self._extract_route_coordinates(route_info)
            
            if not route_coordinates:
                logger.warning(f"No route coordinates available for OSM caching - route {route.id}")
                return
            
            # Cache amenities with 10-mile corridor
            cached_count = self.overpass_service.cache_amenities_for_route(
                route_coordinates, corridor_width_miles=10
            )
            
            logger.info(f"✅ Cached {cached_count} OSM amenities for route {route.id}")
            
        except Exception as e:
            # Don't fail route calculation if OSM caching fails
            logger.warning(f"⚠️ OSM amenity caching failed for route {route.id}: {str(e)}")
    
    def _extract_route_coordinates(self, route_info):
        """Extract route coordinates from route info for OSM caching."""
        geometry = route_info.get('geometry')
        if not geometry:
            return []
        
        try:
            # Handle different geometry formats
            if isinstance(geometry, str):
                geometry_data = json.loads(geometry)
            else:
                geometry_data = geometry
            
            # Extract coordinates from GeoJSON
            if geometry_data.get('type') == 'LineString':
                return geometry_data['coordinates']  # [[lng, lat], [lng, lat], ...]
            elif isinstance(geometry_data, list):
                return geometry_data
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Could not extract route coordinates: {str(e)}")
            
        return []

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

        # Plan fuel stops based on distance (Assessment requirement: every 1,000 miles)
        # Use OSM fuel stations from cache when available
        fuel_stops_needed = int(total_distance // self.fuel_interval_miles)
        cumulative_fuel_distance = 0
        
        for i in range(fuel_stops_needed):
            # Calculate fuel stop location more accurately
            fuel_stop_distance = (i + 1) * self.fuel_interval_miles
            distance_from_previous = fuel_stop_distance - cumulative_fuel_distance
            fuel_time = int((fuel_stop_distance / total_distance) * total_time)
            
            # Try to find actual fuel station from OSM cache
            fuel_station = self._find_osm_fuel_station_at_distance(route, fuel_stop_distance, total_distance)
            
            if fuel_station:
                # Use real fuel station from OSM
                fuel_stop_location = fuel_station['name'] or f"Fuel Station - Mile {fuel_stop_distance:.0f}"
                fuel_lat = fuel_station['latitude']
                fuel_lng = fuel_station['longitude']
                stop_description = f"Real fuel station: {fuel_station.get('brand', 'Unknown')} - {fuel_station.get('address', 'Address not available')}"
                logger.info(f"✅ Using OSM fuel station: {fuel_stop_location} at ({fuel_lat}, {fuel_lng})")
            else:
                # Fallback to generated location if no OSM data
                fuel_stop_location = self._get_fuel_stop_location(fuel_stop_distance, total_distance, i + 1)
                fuel_lat = None
                fuel_lng = None
                stop_description = f"Mandatory fuel stop #{i+1} (1,000-mile interval) - OSM data not available"
                logger.info(f"⚠️ Using fallback fuel stop location: {fuel_stop_location}")
            
            waypoints.append(
                self._create_waypoint(
                    route,
                    sequence,
                    fuel_stop_location,
                    fuel_lat,
                    fuel_lng,
                    Waypoint.WaypointType.FUEL_STOP,
                    distance_from_previous,
                    fuel_time,
                    30,  # 30 minutes for fueling
                    stop_description,
                )
            )
            cumulative_fuel_distance = fuel_stop_distance
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

    def _get_fuel_stop_location(self, distance_miles, total_distance, stop_number):
        """Generate realistic fuel stop location names."""
        # In a real implementation, this would query truck stop APIs
        # For now, generate realistic names based on distance progression
        progress_percent = (distance_miles / total_distance) * 100
        
        location_templates = [
            f"Travel Center Mile {distance_miles:.0f}",
            f"Truck Stop #{stop_number} - Mile {distance_miles:.0f}",
            f"Fuel Plaza {stop_number} ({progress_percent:.0f}% route)",
            f"Highway Fuel Stop - Mile {distance_miles:.0f}"
        ]
        
        return location_templates[stop_number % len(location_templates)]
    
    def _find_osm_fuel_station_at_distance(self, route, target_distance_miles, total_distance_miles):
        """
        Find the best OSM fuel station near the target distance along the route.
        
        Args:
            route: Route object
            target_distance_miles: Target distance for fuel stop
            total_distance_miles: Total route distance
            
        Returns:
            Dict with fuel station data or None if not found
        """
        try:
            # Get target coordinates along route
            target_coords = self._get_coordinates_at_distance(route, target_distance_miles, total_distance_miles)
            
            if not target_coords:
                logger.debug(f"Could not determine coordinates at mile {target_distance_miles}")
                return None
            
            target_lat, target_lng = target_coords
            
            # Find fuel stations from OSM cache within reasonable distance
            fuel_stations = OSMLocationCache.objects.filter(
                cache_status=OSMLocationCache.CacheStatus.ACTIVE,
                amenity_type__in=[
                    OSMLocationCache.AmenityType.FUEL,
                    OSMLocationCache.AmenityType.TRUCK_STOP,
                    OSMLocationCache.AmenityType.GAS_STATION,
                ],
                truck_accessible=True,  # Prioritize truck-accessible stations
            )
            
            # Filter by distance and find closest one
            best_station = None
            best_distance = float('inf')
            search_radius_miles = 25  # 25-mile search radius
            
            for station in fuel_stations:
                distance_miles = calculate_distance_miles(
                    target_lat, target_lng,
                    float(station.latitude), float(station.longitude)
                )
                
                if distance_miles <= search_radius_miles and distance_miles < best_distance:
                    best_distance = distance_miles
                    best_station = station
            
            if best_station:
                logger.debug(f"Found fuel station {best_distance:.1f} miles from target: {best_station.name}")
                return {
                    'name': best_station.name,
                    'latitude': float(best_station.latitude),
                    'longitude': float(best_station.longitude),
                    'address': best_station.address,
                    'brand': best_station.brand,
                    'amenity_type': best_station.amenity_type,
                    'fuel_types': best_station.fuel_types,
                    'truck_accessible': best_station.truck_accessible,
                    'distance_from_target': best_distance
                }
            
            logger.debug(f"No suitable fuel stations found within {search_radius_miles} miles of mile {target_distance_miles}")
            return None
            
        except Exception as e:
            logger.warning(f"Error finding OSM fuel station: {str(e)}")
            return None
    
    def _get_coordinates_at_distance(self, route, target_distance_miles, total_distance_miles):
        """
        Get lat/lng coordinates at specific distance along the route.
        
        Args:
            route: Route object
            target_distance_miles: Target distance along route
            total_distance_miles: Total route distance
            
        Returns:
            Tuple of (lat, lng) or None if cannot determine
        """
        try:
            # Calculate position ratio along route
            if total_distance_miles == 0:
                return None
            
            position_ratio = target_distance_miles / total_distance_miles
            position_ratio = max(0, min(1, position_ratio))  # Clamp to [0, 1]
            
            # Try to interpolate from route geometry
            geometry_coords = self._interpolate_coordinates_from_route(
                route, target_distance_miles, 'fuel_stop'
            )
            
            if geometry_coords:
                return tuple(geometry_coords)
            
            # Fallback: linear interpolation between trip endpoints
            trip = route.trip
            if (trip.pickup_lat and trip.pickup_lng and 
                trip.dropoff_lat and trip.dropoff_lng):
                
                start_lat = float(trip.pickup_lat)
                start_lng = float(trip.pickup_lng)
                end_lat = float(trip.dropoff_lat)
                end_lng = float(trip.dropoff_lng)
                
                # Linear interpolation
                interp_lat = start_lat + position_ratio * (end_lat - start_lat)
                interp_lng = start_lng + position_ratio * (end_lng - start_lng)
                
                return (interp_lat, interp_lng)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting coordinates at distance {target_distance_miles}: {str(e)}")
            return None

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
        hos_regulation="",
    ):
        """Helper method to create waypoint records with enhanced details."""
        # Get detailed stop reason and HOS regulation reference
        detailed_reason = self._get_detailed_stop_reason(waypoint_type, reason)
        regulation_ref = hos_regulation or self._get_hos_regulation_reference(waypoint_type)
        
        # If coordinates are not provided, interpolate from route geometry
        final_lat, final_lng = self._get_waypoint_coordinates(
            route, lat, lng, distance, waypoint_type
        )
        
        waypoint = Waypoint.objects.create(
            route=route,
            sequence_order=sequence,
            latitude=final_lat,
            longitude=final_lng,
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
            stop_reason=detailed_reason,
            hos_regulation=regulation_ref,
        )
        return waypoint

    def _get_waypoint_coordinates(self, route, lat, lng, distance, waypoint_type):
        """Get coordinates for waypoint, interpolating from route if needed."""
        # If coordinates are provided, use them
        if lat is not None and lng is not None:
            return Decimal(str(lat)), Decimal(str(lng))
        
        # Try to interpolate from route geometry
        try:
            if route.route_geometry:
                coordinates = self._interpolate_coordinates_from_route(
                    route, distance, waypoint_type
                )
                if coordinates:
                    return Decimal(str(coordinates[0])), Decimal(str(coordinates[1]))
        except Exception as e:
            logger.warning(f"Failed to interpolate coordinates: {e}")
        
        # Fallback: use trip coordinates as approximation
        trip = route.trip
        if waypoint_type in ['break_30min', 'break_10hour', 'fuel_stop']:
            # Place break waypoints between pickup and dropoff
            if trip.pickup_lat and trip.pickup_lng and trip.dropoff_lat and trip.dropoff_lng:
                # Simple linear interpolation (midpoint for breaks)
                lat_interp = (float(trip.pickup_lat) + float(trip.dropoff_lat)) / 2
                lng_interp = (float(trip.pickup_lng) + float(trip.dropoff_lng)) / 2
                return Decimal(str(lat_interp)), Decimal(str(lng_interp))
        
        # Final fallback to avoid (0,0)
        if trip.pickup_lat and trip.pickup_lng:
            return trip.pickup_lat, trip.pickup_lng
        elif trip.current_lat and trip.current_lng:
            return trip.current_lat, trip.current_lng
        
        # Only use (0,0) as last resort
        logger.warning(f"Using (0,0) coordinates for waypoint {waypoint_type}")
        return Decimal("0"), Decimal("0")
    
    def _interpolate_coordinates_from_route(self, route, target_distance, waypoint_type):
        """Interpolate coordinates from route geometry based on distance."""
        try:
            geometry_data = route.route_geometry
            if isinstance(geometry_data, str):
                geometry = json.loads(geometry_data)
            else:
                geometry = geometry_data
            
            # Extract coordinate array from GeoJSON
            if geometry.get('type') == 'LineString':
                coords = geometry['coordinates']
            elif isinstance(geometry, list):
                coords = geometry
            else:
                return None
            
            if not coords or len(coords) < 2:
                return None
            
            # Calculate position along route based on distance
            total_distance = float(route.total_distance_miles)
            if total_distance == 0:
                return None
            
            position_ratio = float(target_distance) / total_distance
            position_ratio = max(0, min(1, position_ratio))  # Clamp between 0 and 1
            
            # Find the coordinate at this position
            target_index = position_ratio * (len(coords) - 1)
            index = int(target_index)
            
            if index >= len(coords) - 1:
                # Return last coordinate
                coord = coords[-1]
                return [coord[1], coord[0]]  # Convert [lng, lat] to [lat, lng]
            
            # Interpolate between two coordinates
            coord1 = coords[index]
            coord2 = coords[index + 1]
            
            # Linear interpolation
            fraction = target_index - index
            lat = coord1[1] + fraction * (coord2[1] - coord1[1])
            lng = coord1[0] + fraction * (coord2[0] - coord1[0])
            
            return [lat, lng]
            
        except Exception as e:
            logger.warning(f"Failed to interpolate from route geometry: {e}")
            return None

    def _get_detailed_stop_reason(self, waypoint_type, basic_reason):
        """Provide detailed, regulation-specific stop reasons."""
        reasons = {
            Waypoint.WaypointType.BREAK_30MIN: '30-minute rest break required after 8 hours cumulative driving per FMCSA regulations',
            Waypoint.WaypointType.BREAK_10HOUR: '10-hour consecutive off-duty period required for daily reset',
            Waypoint.WaypointType.FUEL_STOP: 'Mandatory fuel stop - maximum 1,000 miles between fueling as per assessment requirements',
            Waypoint.WaypointType.PICKUP: '1-hour pickup time allocated per assessment requirements for cargo loading',
            Waypoint.WaypointType.DROPOFF: '1-hour delivery time allocated per assessment requirements for cargo unloading',
            Waypoint.WaypointType.REST_STOP: 'Mandatory rest stop required for HOS compliance',
        }
        return reasons.get(waypoint_type, basic_reason)

    def _get_hos_regulation_reference(self, waypoint_type):
        """Get specific HOS regulation reference for waypoint type."""
        regulations = {
            Waypoint.WaypointType.BREAK_30MIN: '49 CFR 395.3(a)(3)(ii)',
            Waypoint.WaypointType.BREAK_10HOUR: '49 CFR 395.3(a)(1)',
            Waypoint.WaypointType.FUEL_STOP: 'Assessment Requirement',
            Waypoint.WaypointType.PICKUP: 'Assessment Requirement - 1hr',
            Waypoint.WaypointType.DROPOFF: 'Assessment Requirement - 1hr',
            Waypoint.WaypointType.REST_STOP: '49 CFR 395.3',
        }
        return regulations.get(waypoint_type, '')

    def _calculate_hos_stops(self, route, trip):
        """Calculate required HOS rest stops with enhanced accuracy."""
        stops = []
        total_distance = float(route.total_distance_miles)
        total_time_hours = route.estimated_driving_time_minutes / 60
        current_cycle_hours = float(trip.current_cycle_used)
        
        # Enhanced HOS compliance calculations
        logger.info(f"Calculating HOS stops: {total_time_hours:.2f}h drive time, {current_cycle_hours:.2f}h cycle used")

        # 30-minute break required after 8 hours cumulative driving (49 CFR 395.3(a)(3)(ii))
        if total_time_hours > 8:
            # Place break at 8-hour mark to maximize efficiency
            break_at_distance = total_distance * (8.0 / total_time_hours)
            break_at_time = 8 * 60  # 8 hours in minutes
            
            stops.append({
                "location": "Rest Area - Mandatory 30-Min Break",
                "type": Waypoint.WaypointType.BREAK_30MIN,
                "distance": break_at_distance,
                "time": break_at_time,
                "duration": 30,
                "reason": "30-minute break required after 8 hours cumulative driving",
            })
            logger.info(f"Added 30-min break at {break_at_distance:.1f} miles ({break_at_time/60:.1f} hours)")

        # 10-hour rest break if exceeding 11-hour driving limit (49 CFR 395.3(a)(1))
        if total_time_hours > 11:
            # Need overnight rest after 11 hours of driving
            break_at_distance = total_distance * (11.0 / total_time_hours)
            break_at_time = 11 * 60  # 11 hours in minutes
            
            stops.append({
                "location": "Truck Stop - Mandatory 10-Hour Rest",
                "type": Waypoint.WaypointType.BREAK_10HOUR,
                "distance": break_at_distance,
                "time": break_at_time,
                "duration": 600,  # 10 hours
                "reason": "10-hour rest break required - exceeded 11-hour daily driving limit",
            })
            logger.info(f"Added 10-hour rest at {break_at_distance:.1f} miles (11-hour limit)")
        
        # Check 70-hour/8-day cycle limit
        elif (current_cycle_hours + total_time_hours) > 70:
            # Need rest to avoid cycle violation
            available_hours = 70 - current_cycle_hours
            break_at_time_hours = min(available_hours - 1, 11)  # Leave 1 hour buffer
            break_at_distance = total_distance * (break_at_time_hours / total_time_hours)
            
            stops.append({
                "location": "Truck Stop - Cycle Limit Rest",
                "type": Waypoint.WaypointType.BREAK_10HOUR,
                "distance": break_at_distance,
                "time": int(break_at_time_hours * 60),
                "duration": 600,  # 10 hours
                "reason": f"10-hour rest break required - approaching 70-hour cycle limit",
            })
            logger.info(f"Added cycle limit rest at {break_at_distance:.1f} miles ({break_at_time_hours:.1f} hours)")
        
        # Check 14-hour driving window if trip spans beyond window
        total_trip_time_with_stops = total_time_hours + len(stops) * 0.5  # Add stop time
        if total_trip_time_with_stops > 14:
            # Trip exceeds 14-hour driving window, need overnight rest
            if not any(stop["type"] == Waypoint.WaypointType.BREAK_10HOUR for stop in stops):
                break_at_distance = total_distance * 0.7  # Strategic placement
                
                stops.append({
                    "location": "Truck Stop - 14-Hour Window Reset",
                    "type": Waypoint.WaypointType.BREAK_10HOUR,
                    "distance": break_at_distance,
                    "time": int(14 * 60),
                    "duration": 600,  # 10 hours
                    "reason": "10-hour rest break required - exceeding 14-hour driving window",
                })
                logger.info(f"Added 14-hour window reset at {break_at_distance:.1f} miles")

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
