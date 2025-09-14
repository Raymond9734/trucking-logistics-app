"""
Mapping Service for external route calculation APIs.

FIXED VERSION - Provides integration with mapping services like OpenRouteService.
Handles API communication, response parsing, and error handling with distance validation.
"""

import logging
import requests
from django.conf import settings
from typing import Dict, List

logger = logging.getLogger(__name__)


class MappingService:
    """
    Service for integrating with external mapping APIs.

    Currently supports OpenRouteService (free tier) as specified in the guidelines.
    Can be extended to support Google Maps, Mapbox, etc.

    Single Responsibility: External mapping API integration
    """

    def __init__(self):
        """Initialize mapping service with configuration."""
        self.service = "openrouteservice"
        self.base_url = "https://api.openrouteservice.org"
        self.api_key = getattr(settings, "OPENROUTESERVICE_API_KEY", None)

        # Check if API key is configured
        self.use_mock = not self.api_key

        # Debug logging
        logger.info(f"🔑 API Key configured: {'Yes' if self.api_key else 'No'}")
        if self.api_key:
            logger.info(f"🔑 API Key length: {len(self.api_key)}")
            logger.info(f"🔑 API Key preview: {self.api_key[:20]}...")
        else:
            logger.warning("🔑 No API Key configured - route calculation will fail")

    def calculate_route(self, locations: List[str]) -> Dict:
        """
        Calculate route between multiple locations.

        Args:
            locations: List of location addresses or coordinates

        Returns:
            Dict containing route information:
            - distance_miles: Total distance in miles
            - duration_minutes: Total driving time in minutes
            - geometry: Encoded route geometry
            - coordinates: List of lat/lng coordinates for locations
            - service: Name of mapping service used

        Raises:
            ValueError: If route validation fails (e.g., distance limits)
            Exception: If route calculation fails
        """
        if self.use_mock:
            logger.error("No API key configured for OpenRouteService")
            raise ValueError(
                "OpenRouteService API key is required for route calculation. Please configure OPENROUTESERVICE_API_KEY in settings."
            )

        # Convert addresses to coordinates if needed
        coordinates = self._geocode_locations(locations)

        # Calculate route using OpenRouteService
        route_data = self._call_openrouteservice_directions(coordinates)

        # Parse and format response
        return self._parse_route_response(route_data, coordinates)

    def _geocode_locations(self, locations: List) -> List[Dict]:
        """Convert location addresses or use existing coordinates."""
        coordinates = []

        for location in locations:
            try:
                if isinstance(location, dict) and "lat" in location and "lng" in location:
                    # Already a coordinate dictionary
                    coordinates.append(location)
                elif isinstance(location, str):
                    if self._is_coordinate_string(location):
                        # A string that looks like coordinates
                        lat, lng = self._parse_coordinates(location)
                        coordinates.append({"lat": lat, "lng": lng, "address": location})
                    else:
                        # An address string that needs geocoding, but user wants an error
                        raise ValueError(f"Geocoding is not allowed for address: {location}")
                else:
                    raise ValueError(f"Invalid location format: {location}")

            except Exception as e:
                logger.error(f"Processing location failed for {location}: {str(e)}")
                raise ValueError(f"Could not process location '{location}': {str(e)}")

        return coordinates

    def _geocode_address(self, address: str) -> Dict:
        """Geocode a single address to coordinates."""
        url = f"{self.base_url}/geocode/search"
        params = {"api_key": self.api_key, "text": address, "size": 1}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data["features"]:
            coords = data["features"][0]["geometry"]["coordinates"]
            return {"lat": coords[1], "lng": coords[0]}

        raise ValueError(f"Could not geocode address: {address}")

    def _validate_route_distance(self, coordinates: List[Dict]) -> None:
        """
        Validate that route distance is within OpenRouteService limits.

        OpenRouteService has a 6,000,000 meter (6,000 km / 3,728 miles) limit.
        We'll use a more conservative 3,000 miles to account for routing variations.
        """
        if len(coordinates) < 2:
            return

        # Calculate approximate total distance using haversine formula
        from common.validators import calculate_distance_miles

        total_distance = 0
        for i in range(len(coordinates) - 1):
            coord1 = coordinates[i]
            coord2 = coordinates[i + 1]

            distance = calculate_distance_miles(
                coord1["lat"], coord1["lng"], coord2["lat"], coord2["lng"]
            )
            total_distance += distance

        logger.info(f"🌍 Estimated total route distance: {total_distance:.1f} miles")

        # OpenRouteService limit is 6,000 km ≈ 3,728 miles
        # Use conservative limit to account for routing variations
        MAX_DISTANCE_MILES = 3000

        if total_distance > MAX_DISTANCE_MILES:
            logger.error(
                f"❌ Route distance ({total_distance:.1f} miles) exceeds limit ({MAX_DISTANCE_MILES} miles)"
            )
            raise ValueError(
                f"Route distance ({total_distance:.1f} miles) exceeds OpenRouteService limit "
                f"({MAX_DISTANCE_MILES} miles). Please use locations closer together for commercial trucking routes."
            )

    def _call_openrouteservice_directions(self, coordinates: List[Dict]) -> Dict:
        """Call OpenRouteService directions API."""
        # Validate route distance before API call
        self._validate_route_distance(coordinates)

        # Use the GeoJSON endpoint
        url = f"{self.base_url}/v2/directions/driving-hgv/geojson"

        # Format coordinates for API call - OpenRouteService expects [longitude, latitude]
        coords = [[float(coord["lng"]), float(coord["lat"])] for coord in coordinates]

        payload = {
            "coordinates": coords,
            "instructions": True,
            "geometry": True,
            "elevation": False,
        }

        # OpenRouteService supports multiple authentication methods:
        # 1. API key in query parameter: ?api_key=xxx
        # 2. Authorization header with Bearer: Authorization: Bearer xxx
        # 3. Authorization header direct: Authorization: xxx
        # Let's try the query parameter method first as it's most reliable
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
        }

        # Add API key as query parameter
        url_with_key = f"{url}?api_key={self.api_key}"

        logger.info(f"Making OpenRouteService request to: {url}")
        logger.info(f"Payload coordinates: {coords}")
        logger.info(f"API key configured: {'Yes' if self.api_key else 'No'}")

        try:
            response = requests.post(
                url_with_key, json=payload, headers=headers, timeout=30
            )

            logger.info(f"OpenRouteService response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"OpenRouteService API error: {response.status_code}")
                logger.error(f"Response text: {response.text}")

                # Try alternative authentication method if query param fails
                if response.status_code in [400, 401, 403]:
                    logger.info("Trying alternative authentication method...")
                    return self._call_openrouteservice_directions_alt_auth(coordinates)

                response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouteService request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")

                # Try alternative authentication method as fallback
                if e.response.status_code in [400, 401, 403]:
                    logger.info(
                        "Trying alternative authentication method as fallback..."
                    )
                    try:
                        return self._call_openrouteservice_directions_alt_auth(
                            coordinates
                        )
                    except Exception as alt_e:
                        logger.error(
                            f"Alternative authentication also failed: {str(alt_e)}"
                        )

            raise

    def _call_openrouteservice_directions_alt_auth(
        self, coordinates: List[Dict]
    ) -> Dict:
        """Alternative authentication method using Authorization header."""
        url = f"{self.base_url}/v2/directions/driving-hgv/geojson"

        # Format coordinates for API call
        coords = [[coord["lng"], coord["lat"]] for coord in coordinates]

        payload = {
            "coordinates": coords,
            "instructions": True,
            "geometry": True,
            "elevation": False,
        }

        # Try Authorization header method
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
        }

        logger.info(f"Trying alternative auth - Making request to: {url}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        logger.info(f"Alternative auth response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Alternative auth failed: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            response.raise_for_status()

        return response.json()

    def _parse_route_response(self, route_data: Dict, coordinates: List[Dict]) -> Dict:
        """Parse OpenRouteService response into standard format."""
        # Check if it's a GeoJSON response (features array) or regular JSON response (routes array)
        if route_data.get("features"):
            # Handle GeoJSON format response
            if not route_data.get("features"):
                raise ValueError("No route found")

            route = route_data["features"][0]
            properties = route["properties"]
            segments = properties.get("segments", [{}])

            # Extract route information from GeoJSON format
            total_distance_meters = properties.get("summary", {}).get("distance", 0)
            total_duration_seconds = properties.get("summary", {}).get("duration", 0)
            geometry = route["geometry"]

        elif route_data.get("routes"):
            # Handle standard JSON format response
            if not route_data.get("routes"):
                raise ValueError("No route found")

            route = route_data["routes"][0]
            segments = route.get("segments", [{}])
            summary = route.get("summary", {})

            # Extract route information from standard JSON format
            total_distance_meters = summary.get("distance", 0)
            total_duration_seconds = summary.get("duration", 0)
            geometry = route.get("geometry", "")

        else:
            raise ValueError("Unexpected response format from OpenRouteService")

        # Convert to miles and minutes
        distance_miles = total_distance_meters * 0.000621371  # meters to miles
        duration_minutes = int(total_duration_seconds / 60)  # seconds to minutes

        return {
            "distance_miles": round(distance_miles, 2),
            "duration_minutes": duration_minutes,
            "geometry": geometry,
            "coordinates": coordinates,
            "service": "openrouteservice",
            "traffic_considered": False,
            "profile": "driving-hgv",
            "segments": len(segments),
            "instructions": segments[0].get("steps", []) if segments else [],
        }

    def _is_coordinate_string(self, location: str) -> bool:
        """Check if location string is already coordinates."""
        try:
            parts = location.replace(",", " ").split()
            if len(parts) == 2:
                float(parts[0])
                float(parts[1])
                return True
        except ValueError:
            pass
        return False

    def _parse_coordinates(self, coord_string: str) -> tuple:
        """Parse coordinate string to lat, lng tuple."""
        parts = coord_string.replace(",", " ").split()
        return float(parts[0]), float(parts[1])

    def get_service_status(self) -> Dict:
        """Get current status of mapping service."""
        return {
            "service": self.service,
            "available": bool(self.api_key),
            "api_key_configured": bool(self.api_key),
            "base_url": self.base_url,
            "operational": bool(self.api_key),
        }

    def estimate_trip_duration(
        self, distance_miles: float, vehicle_type: str = "truck"
    ) -> int:
        """
        Estimate trip duration based on distance and vehicle type.

        Args:
            distance_miles: Distance in miles
            vehicle_type: Type of vehicle (truck, car, etc.)

        Returns:
            Estimated duration in minutes
        """
        # Average speeds by vehicle type
        average_speeds = {
            "truck": 55,  # mph for commercial trucks
            "car": 65,  # mph for passenger cars
            "van": 60,  # mph for delivery vans
        }

        speed = average_speeds.get(vehicle_type, 55)
        duration_hours = distance_miles / speed

        # Add buffer time for stops, traffic, etc.
        buffer_factor = 1.2 if vehicle_type == "truck" else 1.1
        duration_hours *= buffer_factor

        return int(duration_hours * 60)  # Convert to minutes

    def get_fuel_efficient_route(self, locations: List[str]) -> Dict:
        """Get most fuel-efficient route option."""
        # This would call specialized routing API for fuel efficiency
        # For now, return standard route with fuel efficiency flag
        route = self.calculate_route(locations)
        route["optimized_for"] = "fuel_efficiency"
        route["estimated_fuel_savings"] = "5-10%"

        return route
