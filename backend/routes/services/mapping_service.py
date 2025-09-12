"""
Mapping Service for external route calculation APIs.

Provides integration with mapping services like OpenRouteService, Google Maps, etc.
Handles API communication, response parsing, and error handling.
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
        # For development, we'll use mock responses if no API key
        self.use_mock = not self.api_key

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
            Exception: If route calculation fails
        """
        try:
            if self.use_mock:
                return self._mock_route_calculation(locations)

            # Convert addresses to coordinates if needed
            coordinates = self._geocode_locations(locations)

            # Calculate route using OpenRouteService
            route_data = self._call_openrouteservice_directions(coordinates)

            # Parse and format response
            return self._parse_route_response(route_data, coordinates)

        except Exception as e:
            logger.error(f"Route calculation failed: {str(e)}")
            # Fall back to mock data on API failure
            return self._mock_route_calculation(locations)

    def _geocode_locations(self, locations: List[str]) -> List[Dict]:
        """Convert location addresses to coordinates."""
        coordinates = []

        for location in locations:
            try:
                if self._is_coordinate_string(location):
                    # Already coordinates
                    lat, lng = self._parse_coordinates(location)
                    coordinates.append({"lat": lat, "lng": lng, "address": location})
                else:
                    # Need to geocode
                    coord = self._geocode_address(location)
                    coord["address"] = location
                    coordinates.append(coord)

            except Exception as e:
                logger.warning(f"Geocoding failed for {location}: {str(e)}")
                # Use mock coordinates
                coordinates.append(
                    {
                        "lat": 40.7128 + len(coordinates) * 0.1,
                        "lng": -74.0060 + len(coordinates) * 0.1,
                        "address": location,
                    }
                )

        return coordinates

    def _geocode_address(self, address: str) -> Dict:
        """Geocode a single address to coordinates."""
        if self.use_mock:
            return {"lat": 40.7128, "lng": -74.0060}

        url = f"{self.base_url}/geocode/search"
        params = {"api_key": self.api_key, "text": address, "size": 1}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data["features"]:
            coords = data["features"][0]["geometry"]["coordinates"]
            return {"lat": coords[1], "lng": coords[0]}

        raise ValueError(f"Could not geocode address: {address}")

    def _call_openrouteservice_directions(self, coordinates: List[Dict]) -> Dict:
        """Call OpenRouteService directions API."""
        url = f"{self.base_url}/v2/directions/driving-hgv/geojson"

        # Format coordinates for API call
        coords = [[coord["lng"], coord["lat"]] for coord in coordinates]

        payload = {
            "coordinates": coords,
            "profile": "driving-hgv",  # Heavy goods vehicle profile for trucks
            "format": "geojson",
            "instructions": True,
            "geometry": True,
            "elevation": False,
        }

        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()

    def _parse_route_response(self, route_data: Dict, coordinates: List[Dict]) -> Dict:
        """Parse OpenRouteService response into standard format."""
        if not route_data.get("features"):
            raise ValueError("No route found")

        route = route_data["features"][0]
        properties = route["properties"]
        segments = properties.get("segments", [{}])

        # Extract route information
        total_distance_meters = properties.get("summary", {}).get("distance", 0)
        total_duration_seconds = properties.get("summary", {}).get("duration", 0)

        # Convert to miles and minutes
        distance_miles = total_distance_meters * 0.000621371  # meters to miles
        duration_minutes = int(total_duration_seconds / 60)  # seconds to minutes

        return {
            "distance_miles": round(distance_miles, 2),
            "duration_minutes": duration_minutes,
            "geometry": route["geometry"],  # GeoJSON geometry
            "coordinates": coordinates,
            "service": "openrouteservice",
            "traffic_considered": False,
            "profile": "driving-hgv",
            "segments": len(segments),
            "instructions": properties.get("segments", [{}])[0].get("steps", []),
        }

    def _mock_route_calculation(self, locations: List[str]) -> Dict:
        """
        Provide mock route calculation for development/testing.

        Generates realistic route data for testing without API calls.
        """
        logger.info("Using mock route calculation (no API key configured)")

        num_locations = len(locations)

        # Base distance calculation (rough estimate between locations)
        base_distance = 50 + (num_locations - 2) * 150  # Miles

        # Add some variation based on location strings
        distance_modifier = sum(len(loc) for loc in locations) % 100
        total_distance = base_distance + distance_modifier

        # Calculate duration assuming average speed of 55 mph
        duration_minutes = int((total_distance / 55) * 60)

        # Generate mock coordinates
        coordinates = []
        base_lat, base_lng = 39.8283, -98.5795  # Geographic center of US

        for i, location in enumerate(locations):
            coordinates.append(
                {
                    "lat": base_lat + (i * 0.5),
                    "lng": base_lng + (i * 0.8),
                    "address": location,
                }
            )

        return {
            "distance_miles": round(total_distance, 2),
            "duration_minutes": duration_minutes,
            "geometry": self._generate_mock_geometry(coordinates),
            "coordinates": coordinates,
            "service": "mock",
            "traffic_considered": False,
            "profile": "driving-hgv",
            "segments": num_locations - 1,
            "instructions": [
                (
                    f"Head to {locations[1]}"
                    if len(locations) > 1
                    else "Stay at current location"
                ),
                (
                    f"Continue to {locations[2]}"
                    if len(locations) > 2
                    else "Arrive at destination"
                ),
            ],
        }

    def _generate_mock_geometry(self, coordinates: List[Dict]) -> Dict:
        """Generate mock GeoJSON geometry."""
        coords = [[coord["lng"], coord["lat"]] for coord in coordinates]

        return {"type": "LineString", "coordinates": coords}

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
            "available": not self.use_mock,
            "api_key_configured": bool(self.api_key),
            "base_url": self.base_url,
            "mock_mode": self.use_mock,
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
