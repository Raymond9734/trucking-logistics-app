"""
OpenStreetMap Overpass API Service

Fetches amenities (fuel stations, truck stops, etc.) from OpenStreetMap
using the Overpass API and caches them locally for route planning.

Single Responsibility: OSM data fetching and parsing
"""

import logging
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from routes.models.osm_location_cache import OSMLocationCache

logger = logging.getLogger(__name__)


class OverpassService:
    """
    Service for fetching amenities from OpenStreetMap Overpass API.

    Handles:
    - Fetching fuel stations, truck stops, rest areas
    - Parsing OSM data into standardized format
    - Batch updates to cache
    - Rate limiting and error handling
    """

    def __init__(self):
        """Initialize Overpass service with configuration."""
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.timeout = getattr(settings, "OVERPASS_TIMEOUT", 60)
        self.max_retries = getattr(settings, "OVERPASS_MAX_RETRIES", 3)

        # Rate limiting - Overpass API recommends max 2 requests per second
        self.rate_limit_delay = 0.5  # seconds between requests

    def fetch_amenities_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        amenity_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Fetch amenities within a bounding box from Overpass API.

        Args:
            min_lat, min_lon, max_lat, max_lon: Bounding box coordinates
            amenity_types: List of amenity types to fetch (fuel, etc.)

        Returns:
            List of amenity dictionaries parsed from OSM
        """
        if amenity_types is None:
            amenity_types = [
                "fuel",
                "gas_station",
                "restaurant",
                "cafe",
                "toilets",
                "parking",
                "atm",
                "hotel",
            ]

        # Build Overpass QL query
        query = self._build_overpass_query(
            min_lat, min_lon, max_lat, max_lon, amenity_types
        )

        logger.info(
            f"🌍 Fetching OSM amenities for bbox: [{min_lat:.3f}, {min_lon:.3f}, {max_lat:.3f}, {max_lon:.3f}]"
        )
        logger.info(f"🎯 Amenity types: {amenity_types}")
        logger.debug(
            f"📝 Overpass query: {query[:200]}..."
        )  # Log first 200 chars of query

        try:
            # Make request to Overpass API
            response = requests.post(
                self.base_url, data={"data": query}, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse response
            data = response.json()
            elements = data.get("elements", [])

            logger.info(f"✅ Retrieved {len(elements)} OSM elements")

            # Parse and format amenities
            amenities = self._parse_osm_elements(elements)

            logger.info(f"✅ Processed {len(amenities)} amenities for caching")

            return amenities

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Overpass API request failed: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Overpass API response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching OSM data: {str(e)}")
            raise

    def _build_overpass_query(self, min_lat, min_lon, max_lat, max_lon, amenity_types):
        bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        # Build regex for amenity types (remove gas_station, not valid in OSM)
        amenity_regex = "|".join([a for a in amenity_types if a != "gas_station"])

        query = f"""
    [out:json][timeout:{self.timeout}];
    (
    node[amenity~"^({amenity_regex})$"]({bbox});
    way[amenity~"^({amenity_regex})$"]({bbox});
    relation[amenity~"^({amenity_regex})$"]({bbox});

    node[highway~"^(rest_area|services)$"]({bbox});
    way[highway~"^(rest_area|services)$"]({bbox});

    node["amenity"="fuel"]["fuel:HGV"="yes"]({bbox});
    way["amenity"="fuel"]["fuel:HGV"="yes"]({bbox});

    node["truck_stop"="yes"]({bbox});
    way["truck_stop"="yes"]({bbox});
    );
    out center meta;
        """
        return query.strip()

    def _parse_osm_elements(self, elements: List[Dict]) -> List[Dict]:
        """
        Parse OSM elements into standardized amenity format.

        Args:
            elements: Raw OSM elements from Overpass API

        Returns:
            List of parsed amenity dictionaries
        """
        amenities = []

        for element in elements:
            try:
                amenity = self._parse_single_element(element)
                if amenity:
                    amenities.append(amenity)
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to parse OSM element {element.get('id', 'unknown')}: {str(e)}"
                )
                continue

        return amenities

    def _parse_single_element(self, element: Dict) -> Optional[Dict]:
        """
        Parse a single OSM element into amenity format.

        Args:
            element: Single OSM element (node, way, or relation)

        Returns:
            Parsed amenity dictionary or None if not suitable
        """
        tags = element.get("tags", {})

        # Skip if no useful tags
        if not tags:
            return None

        # Determine coordinates
        lat, lon = self._extract_coordinates(element)
        if lat is None or lon is None:
            return None

        # Determine amenity type
        amenity_type = self._determine_amenity_type(tags)
        if not amenity_type:
            return None

        # Extract name and address info
        name = self._extract_name(tags)
        address_info = self._extract_address(tags)

        # Extract fuel and truck information
        fuel_info = self._extract_fuel_info(tags)
        truck_info = self._extract_truck_info(tags)

        # Extract additional amenities
        additional_amenities = self._extract_additional_amenities(tags)

        # Extract operating information
        operating_info = self._extract_operating_info(tags)

        amenity = {
            "osm_id": element["id"],
            "osm_type": element["type"],
            "latitude": lat,
            "longitude": lon,
            "name": name,
            "amenity_type": amenity_type,
            # Address
            "address": address_info.get("full_address"),
            "city": address_info.get("city"),
            "state": address_info.get("state"),
            "country": address_info.get("country"),
            "postal_code": address_info.get("postal_code"),
            # Fuel information
            "fuel_types": fuel_info.get("fuel_types", []),
            "truck_accessible": truck_info.get("truck_accessible", False),
            "hgv_parking": truck_info.get("hgv_parking", False),
            # Additional amenities
            "has_restaurant": additional_amenities.get("restaurant", False),
            "has_toilets": additional_amenities.get("toilets", False),
            "has_atm": additional_amenities.get("atm", False),
            "has_shop": additional_amenities.get("shop", False),
            "has_wifi": additional_amenities.get("wifi", False),
            "has_shower": additional_amenities.get("shower", False),
            # Operating information
            "opening_hours": operating_info.get("opening_hours"),
            "phone": operating_info.get("phone"),
            "website": operating_info.get("website"),
            "brand": operating_info.get("brand"),
            "operator": operating_info.get("operator"),
            # Cache metadata
            "raw_osm_data": tags,
            "osm_last_modified": self._parse_osm_timestamp(element.get("timestamp")),
        }

        return amenity

    def _extract_coordinates(self, element: Dict) -> tuple:
        """Extract lat/lon coordinates from OSM element."""
        if element["type"] == "node":
            return element.get("lat"), element.get("lon")
        elif element["type"] in ["way", "relation"]:
            # Use center coordinates provided by Overpass API
            center = element.get("center", {})
            return center.get("lat"), center.get("lon")
        return None, None

    def _determine_amenity_type(self, tags: Dict) -> Optional[str]:
        """Determine standardized amenity type from OSM tags."""
        # Priority mapping from OSM amenity values to our standard types
        type_mapping = {
            "fuel": OSMLocationCache.AmenityType.FUEL,
            "gas_station": OSMLocationCache.AmenityType.GAS_STATION,
            "charging_station": OSMLocationCache.AmenityType.CHARGING_STATION,
            "restaurant": OSMLocationCache.AmenityType.RESTAURANT,
            "cafe": OSMLocationCache.AmenityType.CAFE,
            "toilets": OSMLocationCache.AmenityType.TOILETS,
            "parking": OSMLocationCache.AmenityType.PARKING,
            "atm": OSMLocationCache.AmenityType.ATM,
            "hotel": OSMLocationCache.AmenityType.HOTEL,
        }

        # Check standard amenity tag
        if "amenity" in tags and tags["amenity"] in type_mapping:
            return type_mapping[tags["amenity"]]

        # Check for highway rest areas/services
        if tags.get("highway") in ["rest_area", "services"]:
            return OSMLocationCache.AmenityType.REST_AREA

        # Check for truck stops
        if tags.get("truck_stop") == "yes" or tags.get("amenity") == "truck_stop":
            return OSMLocationCache.AmenityType.TRUCK_STOP

        # Check for HGV fuel stations
        if tags.get("amenity") == "fuel" and tags.get("fuel:HGV") == "yes":
            return OSMLocationCache.AmenityType.TRUCK_STOP

        return None

    def _extract_name(self, tags: Dict) -> Optional[str]:
        """Extract name from OSM tags."""
        # Try various name tags in order of preference
        for name_key in ["name", "brand", "operator", "official_name"]:
            if name_key in tags:
                return tags[name_key]
        return None

    def _extract_address(self, tags: Dict) -> Dict:
        """Extract address components from OSM tags."""
        address_parts = []

        # Build address from components
        if "addr:housenumber" in tags:
            address_parts.append(tags["addr:housenumber"])
        if "addr:street" in tags:
            address_parts.append(tags["addr:street"])

        return {
            "full_address": ", ".join(address_parts) if address_parts else None,
            "city": tags.get("addr:city"),
            "state": tags.get("addr:state"),
            "country": tags.get("addr:country"),
            "postal_code": tags.get("addr:postcode"),
        }

    def _extract_fuel_info(self, tags: Dict) -> Dict:
        """Extract fuel-related information from OSM tags."""
        fuel_types = []

        # Check for specific fuel types
        fuel_tags = [
            "diesel",
            "petrol",
            "gasoline",
            "lpg",
            "cng",
            "electric",
            "hydrogen",
        ]
        for fuel_type in fuel_tags:
            if tags.get(f"fuel:{fuel_type}") == "yes":
                fuel_types.append(fuel_type)

        # If no specific fuel types but is a fuel amenity, assume basic types
        if not fuel_types and tags.get("amenity") in ["fuel", "gas_station"]:
            fuel_types = ["diesel", "gasoline"]

        return {"fuel_types": fuel_types}

    def _extract_truck_info(self, tags: Dict) -> Dict:
        """Extract truck accessibility information from OSM tags."""
        truck_accessible = (
            tags.get("fuel:HGV") == "yes"
            or tags.get("truck_stop") == "yes"
            or tags.get("hgv") == "yes"
            or tags.get("amenity") == "truck_stop"
            or tags.get("highway") in ["rest_area", "services"]
        )

        hgv_parking = (
            tags.get("parking:hgv") == "yes"
            or tags.get("hgv:parking") == "yes"
            or tags.get("amenity") == "truck_stop"
        )

        return {"truck_accessible": truck_accessible, "hgv_parking": hgv_parking}

    def _extract_additional_amenities(self, tags: Dict) -> Dict:
        """Extract additional amenity flags from OSM tags."""
        return {
            "restaurant": tags.get("restaurant") == "yes" or tags.get("food") == "yes",
            "toilets": tags.get("toilets") == "yes" or tags.get("amenity") == "toilets",
            "atm": tags.get("atm") == "yes" or tags.get("amenity") == "atm",
            "shop": tags.get("shop") is not None,
            "wifi": tags.get("internet_access") in ["yes", "wlan", "wifi"],
            "shower": tags.get("shower") == "yes",
        }

    def _extract_operating_info(self, tags: Dict) -> Dict:
        """Extract operating information from OSM tags."""
        return {
            "opening_hours": tags.get("opening_hours"),
            "phone": tags.get("phone"),
            "website": tags.get("website"),
            "brand": tags.get("brand"),
            "operator": tags.get("operator"),
        }

    def _parse_osm_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse OSM timestamp string to datetime object."""
        if not timestamp_str:
            return None

        try:
            # OSM timestamps are in ISO format: 2023-10-15T10:30:00Z
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def cache_amenities_for_route(
        self,
        route_coordinates: List[List[float]],
        corridor_width_miles: float = 10,
        force_refresh: bool = False,
    ) -> int:
        """
        Cache amenities along a route corridor.

        Args:
            route_coordinates: List of [lng, lat] coordinates defining route
            corridor_width_miles: Width of search corridor in miles
            force_refresh: Whether to force refresh existing cache

        Returns:
            Number of amenities cached
        """
        if not route_coordinates:
            return 0

        # Calculate bounding box with buffer
        lats = [coord[1] for coord in route_coordinates]
        lngs = [coord[0] for coord in route_coordinates]

        # Convert miles to approximate degrees (1 degree ≈ 69 miles)
        buffer_degrees = corridor_width_miles / 69.0

        min_lat = min(lats) - buffer_degrees
        max_lat = max(lats) + buffer_degrees
        min_lon = min(lngs) - buffer_degrees
        max_lon = max(lngs) + buffer_degrees

        logger.info(
            f"🗺️ Caching amenities for route corridor: {corridor_width_miles} miles width"
        )
        logger.info(
            f"📍 Bounding box: [{min_lat:.3f}, {min_lon:.3f}, {max_lat:.3f}, {max_lon:.3f}]"
        )

        # Fetch amenities from Overpass API
        amenities = self.fetch_amenities_in_bbox(
            min_lat,
            min_lon,
            max_lat,
            max_lon,
            amenity_types=["fuel", "gas_station", "restaurant", "toilets", "parking"],
        )

        # Cache amenities in database
        cached_count = self._batch_cache_amenities(amenities, force_refresh)

        logger.info(f"✅ Cached {cached_count} amenities for route corridor")

        return cached_count

    def _batch_cache_amenities(
        self, amenities: List[Dict], force_refresh: bool = False
    ) -> int:
        """
        Batch cache amenities in the database with conflict resolution.

        Args:
            amenities: List of parsed amenity dictionaries
            force_refresh: Whether to force refresh existing entries

        Returns:
            Number of amenities successfully cached
        """
        cached_count = 0

        with transaction.atomic():
            for amenity_data in amenities:
                try:
                    # Check if amenity already exists
                    existing = None
                    try:
                        existing = OSMLocationCache.objects.get(
                            osm_id=amenity_data["osm_id"]
                        )
                    except OSMLocationCache.DoesNotExist:
                        pass

                    if existing and not force_refresh and existing.is_cache_valid():
                        # Skip if cache is still valid and not forcing refresh
                        continue

                    # Prepare cache expiry (30 days from now)
                    cache_expires_at = timezone.now() + timedelta(days=30)
                    amenity_data["cache_expires_at"] = cache_expires_at
                    amenity_data["cache_status"] = OSMLocationCache.CacheStatus.ACTIVE

                    # Convert coordinates to Decimal for database
                    amenity_data["latitude"] = Decimal(str(amenity_data["latitude"]))
                    amenity_data["longitude"] = Decimal(str(amenity_data["longitude"]))

                    if existing:
                        # Update existing entry
                        for key, value in amenity_data.items():
                            if key not in [
                                "id",
                                "created_at",
                            ]:  # Don't update these fields
                                setattr(existing, key, value)
                        existing.save()
                        logger.debug(
                            f"✅ Updated OSM location {amenity_data['osm_id']}"
                        )
                    else:
                        # Create new entry
                        OSMLocationCache.objects.create(**amenity_data)
                        logger.debug(
                            f"✅ Created OSM location {amenity_data['osm_id']}"
                        )

                    cached_count += 1

                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to cache amenity {amenity_data.get('osm_id', 'unknown')}: {str(e)}"
                    )
                    continue

        return cached_count

    def cleanup_stale_cache(self, older_than_days: int = 60) -> int:
        """
        Clean up stale cache entries older than specified days.

        Args:
            older_than_days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        cutoff_date = timezone.now() - timedelta(days=older_than_days)

        stale_entries = OSMLocationCache.objects.filter(
            cache_expires_at__lt=cutoff_date,
            cache_status=OSMLocationCache.CacheStatus.STALE,
        )

        count = stale_entries.count()
        stale_entries.delete()

        logger.info(
            f"🧹 Cleaned up {count} stale OSM cache entries older than {older_than_days} days"
        )

        return count
