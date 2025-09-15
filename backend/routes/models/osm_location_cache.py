"""
OpenStreetMap Location Cache Model.

Caches locations from OpenStreetMap Overpass API to reduce API calls
and improve performance for fuel stations, truck stops, and other amenities.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class OSMLocationCache(models.Model):
    """
    Cache model for OpenStreetMap locations.
    
    Stores fuel stations, truck stops, and other amenities retrieved from
    OpenStreetMap Overpass API with geographic coordinates and metadata.
    
    This model provides caching to:
    - Reduce API calls to Overpass API
    - Improve route calculation performance
    - Store detailed amenity information
    - Enable offline fuel stop planning
    """

    class AmenityType(models.TextChoices):
        """Types of amenities cached from OpenStreetMap."""
        FUEL = 'fuel', 'Fuel Station'
        TRUCK_STOP = 'truck_stop', 'Truck Stop'
        GAS_STATION = 'gas_station', 'Gas Station'
        CHARGING_STATION = 'charging_station', 'EV Charging Station'
        REST_AREA = 'rest_area', 'Rest Area'
        SERVICE_AREA = 'service_area', 'Service Area'
        RESTAURANT = 'restaurant', 'Restaurant'
        CAFE = 'cafe', 'Cafe'
        HOTEL = 'hotel', 'Hotel'
        PARKING = 'parking', 'Parking'
        TOILETS = 'toilets', 'Toilets'
        ATM = 'atm', 'ATM'
        SHOP = 'shop', 'Shop/Convenience Store'

    class CacheStatus(models.TextChoices):
        """Status of cached location data."""
        ACTIVE = 'active', 'Active'
        STALE = 'stale', 'Stale (needs refresh)'
        INVALID = 'invalid', 'Invalid (OSM data changed)'
        ARCHIVED = 'archived', 'Archived'

    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    osm_id = models.BigIntegerField(
        unique=True,
        help_text="OpenStreetMap node/way/relation ID"
    )
    osm_type = models.CharField(
        max_length=10,
        choices=[('node', 'Node'), ('way', 'Way'), ('relation', 'Relation')],
        default='node',
        help_text="Type of OSM element (node, way, relation)"
    )

    # Geographic coordinates
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude in decimal degrees"
    )
    longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude in decimal degrees"
    )

    # Location details
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the location/business"
    )
    amenity_type = models.CharField(
        max_length=50,
        choices=AmenityType.choices,
        help_text="Type of amenity (fuel, truck_stop, etc.)"
    )
    
    # Address information
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Full address if available from OSM"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="City name"
    )
    state = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="State/province"
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Country"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Postal/ZIP code"
    )

    # Fuel-specific information
    fuel_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Available fuel types (diesel, gasoline, etc.)"
    )
    truck_accessible = models.BooleanField(
        default=False,
        help_text="Whether trucks can access this location"
    )
    hgv_parking = models.BooleanField(
        default=False,
        help_text="Has parking for Heavy Goods Vehicles"
    )

    # Additional amenities
    has_restaurant = models.BooleanField(default=False)
    has_toilets = models.BooleanField(default=False)
    has_atm = models.BooleanField(default=False)
    has_shop = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)
    has_shower = models.BooleanField(default=False)

    # Operating information
    opening_hours = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Opening hours in OSM format"
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Phone number"
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Website URL"
    )

    # Brand/operator information
    brand = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Brand name (Shell, BP, Pilot, etc.)"
    )
    operator = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Operator/company name"
    )

    # Cache management
    cache_status = models.CharField(
        max_length=20,
        choices=CacheStatus.choices,
        default=CacheStatus.ACTIVE,
        help_text="Status of this cached location"
    )
    
    # Raw OSM data for reference
    raw_osm_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Raw OSM tags for reference"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    osm_last_modified = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last modified date from OSM"
    )
    cache_expires_at = models.DateTimeField(
        help_text="When this cache entry expires and needs refresh"
    )

    class Meta:
        db_table = 'routes_osm_location_cache'
        verbose_name = 'OSM Location Cache'
        verbose_name_plural = 'OSM Location Cache'
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['amenity_type']),
            models.Index(fields=['truck_accessible']),
            models.Index(fields=['cache_status']),
            models.Index(fields=['cache_expires_at']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['brand']),
        ]

    def __str__(self):
        name_part = f"{self.name} - " if self.name else ""
        return f"{name_part}{self.get_amenity_type_display()} ({self.latitude}, {self.longitude})"

    def is_cache_valid(self):
        """Check if cache entry is still valid."""
        return (
            self.cache_status == self.CacheStatus.ACTIVE and
            self.cache_expires_at > timezone.now()
        )

    def mark_as_stale(self):
        """Mark cache entry as stale for refresh."""
        self.cache_status = self.CacheStatus.STALE
        self.save(update_fields=['cache_status', 'updated_at'])

    def refresh_cache_expiry(self, days=30):
        """Refresh cache expiry date."""
        from datetime import timedelta
        self.cache_expires_at = timezone.now() + timedelta(days=days)
        self.cache_status = self.CacheStatus.ACTIVE
        self.save(update_fields=['cache_expires_at', 'cache_status', 'updated_at'])

    @property
    def coordinates(self):
        """Get coordinates as tuple (lat, lng)."""
        return (float(self.latitude), float(self.longitude))

    @property
    def is_truck_friendly(self):
        """Check if location is suitable for trucks."""
        return (
            self.truck_accessible or 
            self.amenity_type == self.AmenityType.TRUCK_STOP or
            self.hgv_parking
        )

    def calculate_distance_to(self, lat, lng):
        """Calculate distance to given coordinates in miles."""
        from common.validators import calculate_distance_miles
        return calculate_distance_miles(
            float(self.latitude), float(self.longitude),
            lat, lng
        )

    @classmethod
    def find_nearby_fuel_stops(cls, lat, lng, radius_miles=50, limit=10):
        """
        Find nearby fuel stops within radius.
        
        Args:
            lat: Latitude to search around
            lng: Longitude to search around
            radius_miles: Search radius in miles
            limit: Maximum number of results
            
        Returns:
            QuerySet of nearby fuel stops
        """
        # Convert miles to degrees (approximate)
        radius_degrees = radius_miles / 69.0  # 1 degree ≈ 69 miles
        
        return cls.objects.filter(
            cache_status=cls.CacheStatus.ACTIVE,
            amenity_type__in=[
                cls.AmenityType.FUEL,
                cls.AmenityType.TRUCK_STOP,
                cls.AmenityType.GAS_STATION,
            ],
            latitude__range=(lat - radius_degrees, lat + radius_degrees),
            longitude__range=(lng - radius_degrees, lng + radius_degrees),
        ).order_by('?')[:limit]  # Random order for variety

    @classmethod
    def get_truck_stops_along_route(cls, route_coordinates, corridor_width_miles=10):
        """
        Get truck stops along a route corridor.
        
        Args:
            route_coordinates: List of [lng, lat] coordinate pairs
            corridor_width_miles: Width of search corridor in miles
            
        Returns:
            QuerySet of truck stops along route
        """
        if not route_coordinates:
            return cls.objects.none()

        # Create bounding box around route
        lats = [coord[1] for coord in route_coordinates]
        lngs = [coord[0] for coord in route_coordinates]
        
        min_lat = min(lats) - (corridor_width_miles / 69.0)
        max_lat = max(lats) + (corridor_width_miles / 69.0) 
        min_lng = min(lngs) - (corridor_width_miles / 69.0)
        max_lng = max(lngs) + (corridor_width_miles / 69.0)

        return cls.objects.filter(
            cache_status=cls.CacheStatus.ACTIVE,
            amenity_type__in=[
                cls.AmenityType.FUEL,
                cls.AmenityType.TRUCK_STOP,
                cls.AmenityType.GAS_STATION,
            ],
            truck_accessible=True,
            latitude__range=(min_lat, max_lat),
            longitude__range=(min_lng, max_lng),
        )

    def to_waypoint_data(self):
        """Convert to waypoint data format for route planning."""
        return {
            'name': self.name or f"{self.get_amenity_type_display()}",
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'address': self.address or f"{self.city}, {self.state}",
            'amenity_type': self.amenity_type,
            'brand': self.brand,
            'truck_accessible': self.truck_accessible,
            'amenities': {
                'restaurant': self.has_restaurant,
                'toilets': self.has_toilets,
                'atm': self.has_atm,
                'shop': self.has_shop,
                'wifi': self.has_wifi,
                'shower': self.has_shower,
            },
            'fuel_types': self.fuel_types,
            'opening_hours': self.opening_hours,
            'phone': self.phone,
            'website': self.website,
        }
