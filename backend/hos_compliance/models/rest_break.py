"""
Rest Break model for HOS compliance.

Contains the RestBreak model that tracks required rest periods
for HOS compliance.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class RestBreak(models.Model):
    """
    Required rest breaks for HOS compliance.
    
    Tracks mandatory rest periods including 10-hour breaks,
    30-minute breaks, and sleeper berth splits based on FMCSA regulations.
    
    This model represents both planned and completed rest breaks,
    including their regulatory basis and scheduling requirements.
    
    Attributes:
        id: UUID primary key
        trip: Foreign key to Trip
        break_type: Type of break (30-minute, 10-hour, sleeper berth, etc.)
        duration_hours: Duration of the break in hours
        required_at_driving_hours: When this break is required (driving hours)
        required_at_cycle_miles: When this break is required (trip miles)
        location_description: Where the break should be taken
        is_mandatory: Whether this break is mandatory for HOS compliance
        regulation_reference: FMCSA regulation reference
        status: Current status (planned, in_progress, completed, skipped)
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the rest break"
    )
    
    # Link to trip
    trip = models.ForeignKey(
        'routes.Trip',
        on_delete=models.CASCADE,
        related_name='rest_breaks',
        help_text="The trip this rest break belongs to"
    )
    
    # Break type classification
    class BreakType(models.TextChoices):
        THIRTY_MINUTE = '30_minute', '30-Minute Rest Break'
        TEN_HOUR = '10_hour', '10-Hour Off Duty'
        SLEEPER_BERTH_7_3 = 'sleeper_7_3', 'Sleeper Berth 7+3 Split'
        SLEEPER_BERTH_8_2 = 'sleeper_8_2', 'Sleeper Berth 8+2 Split'
        FUEL_STOP = 'fuel_stop', 'Fuel Stop'
        PICKUP_DROPOFF = 'pickup_dropoff', 'Pickup/Dropoff Time'
        LOADING_UNLOADING = 'loading_unloading', 'Loading/Unloading'
        INSPECTION = 'inspection', 'Vehicle Inspection'
        MEAL_BREAK = 'meal_break', 'Meal Break'
    
    break_type = models.CharField(
        max_length=20,
        choices=BreakType.choices,
        help_text="Type of rest break"
    )
    
    # Break duration
    duration_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(Decimal('0.5')), MaxValueValidator(Decimal('34'))],
        help_text="Break duration in hours"
    )
    
    # When break is needed
    required_at_driving_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text="Cumulative driving hours when this break is required"
    )
    
    required_at_cycle_miles = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Trip miles when this break is required (for fuel stops)"
    )
    
    # Break location
    location_description = models.CharField(
        max_length=200,
        help_text="Description of where break should be taken"
    )
    
    # Regulatory compliance
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Whether this break is mandatory for HOS compliance"
    )
    
    regulation_reference = models.CharField(
        max_length=50, 
        blank=True,
        help_text="FMCSA regulation reference (e.g., '395.3(a)(3)')"
    )
    
    # Priority level
    class Priority(models.TextChoices):
        LOW = 'low', 'Low Priority'
        MEDIUM = 'medium', 'Medium Priority'
        HIGH = 'high', 'High Priority'
        CRITICAL = 'critical', 'Critical (Required)'
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Priority level of this break"
    )
    
    # Break status
    class BreakStatus(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'
        RESCHEDULED = 'rescheduled', 'Rescheduled'
    
    status = models.CharField(
        max_length=20,
        choices=BreakStatus.choices,
        default=BreakStatus.PLANNED,
        help_text="Current status of the break"
    )
    
    # Timing information
    scheduled_start_time = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this break is scheduled to start"
    )
    
    actual_start_time = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this break actually started"
    )
    
    actual_end_time = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this break actually ended"
    )
    
    # Additional information
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this break"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this break was planned"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this break was last updated"
    )
    
    class Meta:
        db_table = 'hos_compliance_restbreak'
        ordering = ['required_at_driving_hours']
        verbose_name = 'Rest Break'
        verbose_name_plural = 'Rest Breaks'
        indexes = [
            models.Index(fields=['trip', 'required_at_driving_hours']),
            models.Index(fields=['break_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_mandatory']),
        ]
    
    def __str__(self):
        """Return string representation of the rest break."""
        return f"{self.get_break_type_display()} - {self.duration_hours}h at {self.required_at_driving_hours}h driving"
    
    @property
    def duration_minutes(self):
        """Get duration in minutes."""
        return int(float(self.duration_hours) * 60)
    
    @property
    def actual_duration_hours(self):
        """Calculate actual duration if break has start and end times."""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return round(delta.total_seconds() / 3600, 1)
        return None
    
    def is_hos_required(self):
        """Check if this break is required by HOS regulations."""
        return self.break_type in [
            self.BreakType.THIRTY_MINUTE,
            self.BreakType.TEN_HOUR,
            self.BreakType.SLEEPER_BERTH_7_3,
            self.BreakType.SLEEPER_BERTH_8_2,
        ]
    
    def get_regulation_description(self):
        """Get description of the HOS regulation this break satisfies."""
        descriptions = {
            self.BreakType.THIRTY_MINUTE: "30-minute rest break after 8 hours driving (395.3(a)(3)(ii))",
            self.BreakType.TEN_HOUR: "10 consecutive hours off duty (395.3(a)(1))",
            self.BreakType.SLEEPER_BERTH_7_3: "7-hour sleeper berth + 3-hour off duty split (395.1(g))",
            self.BreakType.SLEEPER_BERTH_8_2: "8-hour sleeper berth + 2-hour off duty split (395.1(g))",
        }
        return descriptions.get(self.break_type, self.regulation_reference or "Not HOS required")
    
    def can_be_skipped(self):
        """Check if this break can be skipped without HOS violation."""
        return not self.is_mandatory or self.break_type in [
            self.BreakType.FUEL_STOP,
            self.BreakType.MEAL_BREAK,
        ]
    
    def get_recommended_location_types(self):
        """Get recommended location types for this break."""
        location_types = {
            self.BreakType.THIRTY_MINUTE: ["Rest area", "Truck stop", "Service plaza"],
            self.BreakType.TEN_HOUR: ["Truck stop with parking", "Rest area", "Company terminal"],
            self.BreakType.SLEEPER_BERTH_7_3: ["Truck stop with sleeper parking", "Rest area"],
            self.BreakType.SLEEPER_BERTH_8_2: ["Truck stop with sleeper parking", "Rest area"],
            self.BreakType.FUEL_STOP: ["Gas station", "Truck stop", "Fuel depot"],
            self.BreakType.PICKUP_DROPOFF: ["Customer location", "Warehouse", "Distribution center"],
            self.BreakType.LOADING_UNLOADING: ["Customer location", "Warehouse", "Loading dock"],
            self.BreakType.INSPECTION: ["Truck stop", "Inspection station", "Company terminal"],
            self.BreakType.MEAL_BREAK: ["Restaurant", "Truck stop", "Rest area"],
        }
        return location_types.get(self.break_type, ["Any suitable location"])
    
    def validate_break_timing(self):
        """Validate that break timing is reasonable."""
        errors = []
        
        if self.duration_hours <= 0:
            errors.append("Break duration must be greater than 0")
        
        if self.required_at_driving_hours < 0:
            errors.append("Required driving hours cannot be negative")
        
        # Validate 30-minute break timing
        if self.break_type == self.BreakType.THIRTY_MINUTE:
            if self.required_at_driving_hours > 8:
                errors.append("30-minute break should occur by 8 hours of driving")
            if self.duration_hours < 0.5:
                errors.append("30-minute break must be at least 0.5 hours")
        
        # Validate 10-hour break
        if self.break_type == self.BreakType.TEN_HOUR:
            if self.duration_hours < 10:
                errors.append("10-hour break must be at least 10 hours")
        
        return errors
