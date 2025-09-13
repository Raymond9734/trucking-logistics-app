"""
Waypoint model for routes app.

Contains the Waypoint model that represents individual points along a route
including mandatory stops for HOS compliance.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Waypoint(models.Model):
    """
    Individual waypoints along a route including stops.
    
    This includes both route waypoints and mandatory stops (rest stops, fuel stops).
    Each waypoint represents a specific location along the planned route.
    
    Attributes:
        id: UUID primary key
        route: Foreign key to Route
        sequence_order: Order of waypoint in the route (0-based)
        latitude/longitude: GPS coordinates of the waypoint
        address: Human-readable address
        waypoint_type: Type of waypoint (origin, pickup, dropoff, rest_stop, etc.)
        distance_from_previous_miles: Distance from previous waypoint
        estimated_time_from_previous_minutes: Time from previous waypoint
        is_mandatory_stop: Whether this is a mandatory stop
        estimated_stop_duration_minutes: How long to stop here
        stop_reason: Reason for the stop
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the waypoint"
    )
    
    # Foreign key to route
    route = models.ForeignKey(
        'routes.Route',  # Use string reference to avoid circular imports
        on_delete=models.CASCADE,
        related_name='waypoints',
        help_text="The route this waypoint belongs to"
    )
    
    # Waypoint position in route
    sequence_order = models.PositiveIntegerField(
        help_text="Order of waypoint in the route (0-based)"
    )
    
    # Geographic location
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        help_text="Waypoint latitude (-90 to 90 degrees)"
    )
    longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7,
        help_text="Waypoint longitude (-180 to 180 degrees)"
    )
    
    address = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Human-readable address of waypoint"
    )
    
    # Waypoint type classification
    class WaypointType(models.TextChoices):
        ORIGIN = 'origin', 'Origin (Current Location)'
        PICKUP = 'pickup', 'Pickup Location'
        DROPOFF = 'dropoff', 'Dropoff Location'
        REST_STOP = 'rest_stop', 'Mandatory Rest Stop'
        FUEL_STOP = 'fuel_stop', 'Fuel Stop'
        BREAK_30MIN = 'break_30min', '30-Minute Break'
        BREAK_10HOUR = 'break_10hour', '10-Hour Rest Break'
        ROUTE_POINT = 'route_point', 'Route Point'
        CHECKPOINT = 'checkpoint', 'Checkpoint'
    
    waypoint_type = models.CharField(
        max_length=20,
        choices=WaypointType.choices,
        help_text="Type/purpose of this waypoint"
    )
    
    # Distance and time from previous waypoint
    distance_from_previous_miles = models.DecimalField(
        max_digits=7, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Distance from previous waypoint in miles"
    )
    
    estimated_time_from_previous_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Estimated travel time from previous waypoint in minutes"
    )
    
    # Stop information
    is_mandatory_stop = models.BooleanField(
        default=False,
        help_text="Whether this is a mandatory stop (rest/fuel/break)"
    )
    
    estimated_stop_duration_minutes = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(2040)],  # Max 34 hours
        help_text="Estimated stop duration in minutes"
    )
    
    stop_reason = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Reason for stop (e.g., '10-hour rest break', 'Fuel stop')"
    )
    
    # HOS regulation reference
    hos_regulation = models.CharField(
        max_length=50,
        blank=True,
        help_text="HOS regulation reference (e.g., '395.3(a)(2)')"
    )
    
    # Additional waypoint metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When waypoint was created"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this waypoint"
    )
    
    class Meta:
        db_table = 'routes_waypoint'
        ordering = ['route', 'sequence_order']
        unique_together = ['route', 'sequence_order']
        verbose_name = 'Waypoint'
        verbose_name_plural = 'Waypoints'
        indexes = [
            models.Index(fields=['route', 'sequence_order']),
            models.Index(fields=['waypoint_type']),
            models.Index(fields=['is_mandatory_stop']),
        ]
    
    def __str__(self):
        """Return string representation of the waypoint."""
        return f"Waypoint {self.sequence_order}: {self.waypoint_type} ({self.address or 'No address'})"
    
    def save(self, *args, **kwargs):
        """Override save to validate coordinates."""
        # Validate latitude
        if not (-90 <= float(self.latitude) <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        
        # Validate longitude
        if not (-180 <= float(self.longitude) <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")
        
        super().save(*args, **kwargs)
    
    @property
    def estimated_time_from_previous_hours(self):
        """Get estimated time from previous waypoint in hours."""
        return round(self.estimated_time_from_previous_minutes / 60, 2)
    
    @property
    def estimated_stop_duration_hours(self):
        """Get estimated stop duration in hours."""
        return round(self.estimated_stop_duration_minutes / 60, 2)
    
    def get_coordinates(self):
        """Get coordinates as a tuple."""
        return (float(self.latitude), float(self.longitude))
    
    def is_hos_required_stop(self):
        """Check if this is an HOS regulation required stop."""
        return self.waypoint_type in [
            self.WaypointType.REST_STOP,
            self.WaypointType.BREAK_30MIN,
            self.WaypointType.BREAK_10HOUR,
        ]
    
    def is_trip_location(self):
        """Check if this is a main trip location (origin, pickup, dropoff)."""
        return self.waypoint_type in [
            self.WaypointType.ORIGIN,
            self.WaypointType.PICKUP,
            self.WaypointType.DROPOFF,
        ]
    
    def get_stop_type_display_name(self):
        """Get a user-friendly display name for the stop type."""
        type_names = {
            self.WaypointType.ORIGIN: "Starting Location",
            self.WaypointType.PICKUP: "Pickup Location",
            self.WaypointType.DROPOFF: "Delivery Location",
            self.WaypointType.REST_STOP: "Rest Stop",
            self.WaypointType.FUEL_STOP: "Fuel Stop",
            self.WaypointType.BREAK_30MIN: "30-Minute Break",
            self.WaypointType.BREAK_10HOUR: "10-Hour Rest Period",
            self.WaypointType.ROUTE_POINT: "Route Point",
            self.WaypointType.CHECKPOINT: "Checkpoint",
        }
        return type_names.get(self.waypoint_type, self.get_waypoint_type_display())
    
    def calculate_cumulative_distance_miles(self):
        """Calculate cumulative distance from route start to this waypoint."""
        previous_waypoints = self.route.waypoints.filter(
            sequence_order__lt=self.sequence_order
        )
        
        cumulative_distance = sum(
            float(wp.distance_from_previous_miles) 
            for wp in previous_waypoints
        ) + float(self.distance_from_previous_miles)
        
        return round(cumulative_distance, 2)
    
    def calculate_cumulative_time_minutes(self):
        """Calculate cumulative time from route start to this waypoint."""
        previous_waypoints = self.route.waypoints.filter(
            sequence_order__lt=self.sequence_order
        )
        
        cumulative_time = sum(
            wp.estimated_time_from_previous_minutes + wp.estimated_stop_duration_minutes
            for wp in previous_waypoints
        ) + self.estimated_time_from_previous_minutes
        
        return cumulative_time
