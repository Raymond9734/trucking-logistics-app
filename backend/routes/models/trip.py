"""
Trip model for routes app.

Contains the main Trip model that represents a driver's trip with locations
and HOS tracking information.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Trip(models.Model):
    """
    Main trip model containing all trip details and inputs.
    
    This is the primary entity that drivers interact with to plan their routes
    and generate HOS-compliant driving schedules.
    
    Attributes:
        id: UUID primary key for security and scalability
        current_location: Driver's current location (address)
        current_lat/lng: Current location coordinates
        pickup_location: Pickup address and coordinates
        dropoff_location: Dropoff address and coordinates
        current_cycle_used: Hours already used in 8-day cycle (0-70)
        driver_name: Driver's full name
        status: Trip status (planned, in_progress, completed, cancelled)
        total_distance_miles: Calculated total trip distance
        estimated_driving_time_hours: Estimated driving time
    """
    
    # Use UUID for better security and scalability
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the trip"
    )
    
    # Current location (required input from assessment)
    current_location = models.CharField(
        max_length=255,
        help_text="Current driver location (address or coordinates)"
    )
    current_lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Current location latitude (-90 to 90)"
    )
    current_lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Current location longitude (-180 to 180)"
    )
    
    # Pickup location (required input from assessment)
    pickup_location = models.CharField(
        max_length=255,
        help_text="Pickup location address"
    )
    pickup_lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Pickup location latitude (-90 to 90)"
    )
    pickup_lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Pickup location longitude (-180 to 180)"
    )
    
    # Dropoff location (required input from assessment)
    dropoff_location = models.CharField(
        max_length=255,
        help_text="Dropoff location address"
    )
    dropoff_lat = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Dropoff location latitude (-90 to 90)"
    )
    dropoff_lng = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        null=True, 
        blank=True,
        help_text="Dropoff location longitude (-180 to 180)"
    )
    
    # HOS tracking (required input from assessment)
    current_cycle_used = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Current cycle hours used (0-70 hours for 8-day cycle)"
    )
    
    # Driver information
    driver_name = models.CharField(
        max_length=100,
        help_text="Driver's full name"
    )
    
    # Trip metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the trip was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the trip was last updated"
    )
    
    # Trip status choices
    class StatusChoices(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PLANNED,
        help_text="Current status of the trip"
    )
    
    # Route calculation results (populated after route calculation)
    total_distance_miles = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Total trip distance in miles"
    )
    estimated_driving_time_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated driving time in hours"
    )
    
    class Meta:
        db_table = 'routes_trip'
        ordering = ['-created_at']
        verbose_name = 'Trip'
        verbose_name_plural = 'Trips'
        indexes = [
            models.Index(fields=['driver_name']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        """Return string representation of the trip."""
        return f"Trip {self.id.hex[:8]} - {self.driver_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        # Validate current_cycle_used is within valid range
        if self.current_cycle_used is not None and self.current_cycle_used > 70:
            raise ValueError("Current cycle used cannot exceed 70 hours")
        
        # Validate coordinates if provided
        if self.current_lat is not None:
            if not (-90 <= float(self.current_lat) <= 90):
                raise ValueError("Current latitude must be between -90 and 90")
        if self.current_lng is not None:
            if not (-180 <= float(self.current_lng) <= 180):
                raise ValueError("Current longitude must be between -180 and 180")
        
        super().save(*args, **kwargs)
    
    @property
    def has_coordinates(self):
        """Check if trip has all coordinate information."""
        return all([
            self.current_lat, self.current_lng,
            self.pickup_lat, self.pickup_lng,
            self.dropoff_lat, self.dropoff_lng
        ])
    
    @property
    def available_cycle_hours(self):
        """Calculate available hours in current 8-day cycle."""
        return max(0, 70 - float(self.current_cycle_used))
    
    def get_locations_list(self):
        """Get list of trip locations in order."""
        return [
            {
                'type': 'current',
                'address': self.current_location,
                'lat': self.current_lat,
                'lng': self.current_lng
            },
            {
                'type': 'pickup',
                'address': self.pickup_location,
                'lat': self.pickup_lat,
                'lng': self.pickup_lng
            },
            {
                'type': 'dropoff',
                'address': self.dropoff_location,
                'lat': self.dropoff_lat,
                'lng': self.dropoff_lng
            }
        ]
    
    def can_start_trip(self):
        """Check if trip can be started based on HOS regulations."""
        if self.current_cycle_used >= 70:
            return False, "70-hour cycle limit reached"
        
        if self.status != self.StatusChoices.PLANNED:
            return False, f"Trip is already {self.status}"
        
        return True, "Trip can be started"
    
    def update_route_results(self, distance_miles, driving_time_hours):
        """Update trip with route calculation results."""
        self.total_distance_miles = distance_miles
        self.estimated_driving_time_hours = driving_time_hours
        self.save()
