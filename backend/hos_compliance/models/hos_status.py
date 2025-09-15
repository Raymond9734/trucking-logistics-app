"""
HOS Status model for HOS compliance tracking.

Contains the HOSStatus model that tracks current Hours of Service
compliance status for drivers.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta


class HOSStatus(models.Model):
    """
    Current Hours of Service status for a driver.
    
    Tracks available hours and compliance with 70hr/8day, 14hr window,
    and 11hr driving limits as per FMCSA regulations.
    
    This model implements the core HOS business logic and tracks:
    - Current cycle hours (70hr/8day rule)
    - Current duty period hours (14hr window)
    - Current driving hours (11hr limit)
    - 30-minute break requirements
    - Next required rest periods
    
    Attributes:
        id: UUID primary key
        trip: One-to-one relationship with Trip
        current_cycle_hours: Hours used in current 8-day cycle
        available_cycle_hours: Hours remaining in cycle
        current_duty_period_hours: Hours on duty in current 14hr window
        available_duty_period_hours: Hours remaining in duty period
        current_driving_hours: Hours driven in current duty period
        available_driving_hours: Hours remaining for driving
        last_duty_status_change: When duty status was last changed
        current_duty_status: Current duty status
        hours_since_last_break: Hours driven since last 30-min break
        needs_30_minute_break: Whether 30-min break is required
        can_drive: Whether driver is currently allowed to drive
        violation_reason: Reason why driver cannot drive
        next_required_rest_hours: Hours of rest required before next duty period
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the HOS status"
    )
    
    # Link to trip
    trip = models.OneToOneField(
        'routes.Trip',
        on_delete=models.CASCADE,
        related_name='hos_status',
        help_text="The trip this HOS status belongs to"
    )
    
    # Current cycle status (70hr/8day rule)
    current_cycle_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Current hours used in 8-day cycle (max 70)"
    )
    
    available_cycle_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Available hours remaining in 8-day cycle"
    )
    
    # Current duty period status (14hr window)
    current_duty_period_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        default=0,
        help_text="Hours on duty in current 14-hour window"
    )
    
    available_duty_period_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        default=14,
        help_text="Available hours remaining in 14-hour window"
    )
    
    # Current driving status (11hr limit)
    current_driving_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        default=0,
        help_text="Hours driven in current duty period"
    )
    
    available_driving_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        default=11,
        help_text="Available driving hours remaining"
    )
    
    # Last duty status change
    last_duty_status_change = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When duty status was last changed"
    )
    
    # Current duty status
    class DutyStatus(models.TextChoices):
        OFF_DUTY = 'off_duty', 'Off Duty'
        SLEEPER_BERTH = 'sleeper_berth', 'Sleeper Berth'
        DRIVING = 'driving', 'Driving'
        ON_DUTY_NOT_DRIVING = 'on_duty_not_driving', 'On Duty (Not Driving)'
    
    current_duty_status = models.CharField(
        max_length=20,
        choices=DutyStatus.choices,
        default=DutyStatus.OFF_DUTY,
        help_text="Current duty status of the driver"
    )
    
    # 30-minute break tracking
    hours_since_last_break = models.DecimalField(
        max_digits=3, 
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Hours driven since last 30-minute break"
    )
    
    needs_30_minute_break = models.BooleanField(
        default=False,
        help_text="Whether driver needs 30-minute break (after 8 hours driving)"
    )
    
    # Compliance flags
    can_drive = models.BooleanField(
        default=True,
        help_text="Whether driver is currently allowed to drive"
    )
    
    violation_reason = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Reason why driver cannot drive (if can_drive=False)"
    )
    
    # Next required rest period
    next_required_rest_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=1,
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(34)],
        help_text="Hours of rest required before next duty period"
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this status was last calculated"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this HOS status was created"
    )
    
    class Meta:
        db_table = 'hos_compliance_status'
        verbose_name = 'HOS Status'
        verbose_name_plural = 'HOS Statuses'
        indexes = [
            models.Index(fields=['trip']),
            models.Index(fields=['can_drive']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        """Return string representation of the HOS status."""
        return f"HOS Status for {self.trip.driver_name} - {self.available_driving_hours}h driving available"
    
    def calculate_available_hours(self):
        """Calculate available hours based on HOS regulations."""
        
        # Calculate available hours for each limit
        self.available_cycle_hours = max(0, Decimal('70') - self.current_cycle_hours)
        self.available_duty_period_hours = max(0, Decimal('14') - self.current_duty_period_hours)
        self.available_driving_hours = max(0, Decimal('11') - self.current_driving_hours)
        
        # Check if 30-minute break is needed (after 8 hours of driving)
        self.needs_30_minute_break = self.hours_since_last_break >= 8
        
        # Determine if driver can drive
        self.can_drive = True
        violation_reasons = []
        
        if self.available_cycle_hours <= 0:
            self.can_drive = False
            violation_reasons.append("70-hour/8-day limit reached")
        
        if self.available_duty_period_hours <= 0:
            self.can_drive = False
            violation_reasons.append("14-hour duty period limit reached")
        
        if self.available_driving_hours <= 0:
            self.can_drive = False
            violation_reasons.append("11-hour driving limit reached")
        
        if self.needs_30_minute_break:
            self.can_drive = False
            violation_reasons.append("30-minute break required after 8 hours driving")
        
        self.violation_reason = "; ".join(violation_reasons)
        
        # Determine next required rest
        if not self.can_drive:
            if self.needs_30_minute_break:
                self.next_required_rest_hours = Decimal('0.5')  # 30 minutes
            else:
                self.next_required_rest_hours = Decimal('10')  # 10 hours off duty
        
        self.save()
    
    def get_maximum_continuous_driving_hours(self):
        """Get maximum hours driver can drive continuously."""
        
        # Consider all limits
        limits = [
            self.available_cycle_hours,
            self.available_duty_period_hours,
            self.available_driving_hours,
            Decimal('8') - self.hours_since_last_break if not self.needs_30_minute_break else Decimal('0')
        ]
        
        return max(Decimal('0'), min(limits))
    
    def get_status_summary(self):
        """Get a summary of current HOS status."""
        return {
            'can_drive': self.can_drive,
            'violation_reason': self.violation_reason,
            'available_cycle_hours': float(self.available_cycle_hours),
            'available_duty_period_hours': float(self.available_duty_period_hours),
            'available_driving_hours': float(self.available_driving_hours),
            'needs_30_minute_break': self.needs_30_minute_break,
            'hours_since_last_break': float(self.hours_since_last_break),
            'next_required_rest_hours': float(self.next_required_rest_hours),
            'current_duty_status': self.current_duty_status,
            'maximum_continuous_driving_hours': float(self.get_maximum_continuous_driving_hours())
        }
