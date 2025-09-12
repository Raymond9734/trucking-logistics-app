"""
Daily Log model for ELD compliance.

Contains the DailyLog model that represents a complete 24-hour
period log as required by FMCSA regulations.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta, time


class DailyLog(models.Model):
    """
    Daily log sheet for ELD compliance.
    
    Represents a complete 24-hour period log as required by FMCSA regulations.
    This matches the format shown in the HOS regulations document and includes
    all required fields for compliance.
    
    Attributes:
        id: UUID primary key
        trip: Foreign key to Trip
        log_date: Date this log covers (24-hour period)
        driver_name: Driver's full legal name
        co_driver_name: Co-driver's name (if applicable)
        carrier_name: Motor carrier name
        carrier_main_office_address: Main office address
        vehicle_number: Truck/tractor number or license plate
        trailer_number: Trailer number (if applicable)
        total_miles_driving_today: Total miles driven during 24-hour period
        total_hours_*: Total hours for each duty status
        period_start_time: Starting time for 24-hour period
        shipping_document_numbers: Shipping document info
        is_certified: Driver certification flag
        driver_signature_date: When driver signed the log
        remarks: Remarks section content
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the daily log"
    )
    
    # Link to trip
    trip = models.ForeignKey(
        'routes.Trip',
        on_delete=models.CASCADE,
        related_name='daily_logs',
        help_text="The trip this daily log belongs to"
    )
    
    # Log date (the 24-hour period this log covers)
    log_date = models.DateField(
        help_text="Date this log covers (24-hour period starting time)"
    )
    
    # Driver information (required on log sheet)
    driver_name = models.CharField(
        max_length=100,
        help_text="Driver's full legal name"
    )
    
    co_driver_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Co-driver's name (if applicable)"
    )
    
    # Carrier information (required on log sheet)
    carrier_name = models.CharField(
        max_length=200,
        help_text="Motor carrier name"
    )
    
    carrier_main_office_address = models.CharField(
        max_length=300,
        help_text="Main office address (city, state sufficient)"
    )
    
    # Vehicle information (required on log sheet)
    vehicle_number = models.CharField(
        max_length=50,
        help_text="Truck/tractor number or license plate"
    )
    
    trailer_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Trailer number (if applicable)"
    )
    
    # Daily totals (calculated from duty status records)
    total_miles_driving_today = models.DecimalField(
        max_digits=6, 
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total miles driven during this 24-hour period"
    )
    
    total_hours_off_duty = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Total off-duty hours"
    )
    
    total_hours_sleeper_berth = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Total sleeper berth hours"
    )
    
    total_hours_driving = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text="Total driving hours"
    )
    
    total_hours_on_duty_not_driving = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        help_text="Total on-duty not driving hours"
    )
    
    # 24-hour period starting time (as designated by carrier)
    period_start_time = models.TimeField(
        default=time(0, 0),  # Midnight
        help_text="Starting time for 24-hour period (usually midnight)"
    )
    
    # Shipping documents
    shipping_document_numbers = models.TextField(
        blank=True,
        help_text="Shipping document numbers or shipper/commodity info"
    )
    
    # Driver certification
    is_certified = models.BooleanField(
        default=False,
        help_text="Driver certification that entries are true and correct"
    )
    
    driver_signature_date = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When driver signed/certified the log"
    )
    
    # Remarks section content
    remarks = models.TextField(
        blank=True,
        help_text="Remarks including city/state for duty status changes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this daily log was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this daily log was last updated"
    )
    
    class Meta:
        db_table = 'eld_logs_dailylog'
        ordering = ['-log_date']
        unique_together = ['trip', 'log_date']
        verbose_name = 'Daily Log'
        verbose_name_plural = 'Daily Logs'
        indexes = [
            models.Index(fields=['trip', 'log_date']),
            models.Index(fields=['driver_name']),
            models.Index(fields=['log_date']),
        ]
    
    def __str__(self):
        """Return string representation of the daily log."""
        return f"Daily Log {self.log_date} - {self.driver_name}"
    
    def calculate_totals(self):
        """Calculate total hours for each duty status from duty status records."""
        duty_records = self.duty_status_records.all()
        
        # Initialize totals
        self.total_hours_off_duty = Decimal('0')
        self.total_hours_sleeper_berth = Decimal('0')
        self.total_hours_driving = Decimal('0')
        self.total_hours_on_duty_not_driving = Decimal('0')
        
        # Calculate totals from duty status records
        for record in duty_records:
            duration_hours = Decimal(str(record.duration_minutes)) / Decimal('60')
            
            if record.duty_status == 'off_duty':
                self.total_hours_off_duty += duration_hours
            elif record.duty_status == 'sleeper_berth':
                self.total_hours_sleeper_berth += duration_hours
            elif record.duty_status == 'driving':
                self.total_hours_driving += duration_hours
            elif record.duty_status == 'on_duty_not_driving':
                self.total_hours_on_duty_not_driving += duration_hours
        
        # Round to nearest 0.25 hours (15 minutes) for ELD compliance
        self.total_hours_off_duty = self._round_to_quarter_hour(self.total_hours_off_duty)
        self.total_hours_sleeper_berth = self._round_to_quarter_hour(self.total_hours_sleeper_berth)
        self.total_hours_driving = self._round_to_quarter_hour(self.total_hours_driving)
        self.total_hours_on_duty_not_driving = self._round_to_quarter_hour(self.total_hours_on_duty_not_driving)
        
        self.save()
    
    def _round_to_quarter_hour(self, hours):
        """Round hours to nearest 0.25 for ELD compliance."""
        return (hours * 4).quantize(Decimal('1')) / 4
    
    @property
    def total_hours_sum(self):
        """Get sum of all duty status hours."""
        return (
            self.total_hours_off_duty + 
            self.total_hours_sleeper_berth + 
            self.total_hours_driving + 
            self.total_hours_on_duty_not_driving
        )
    
    @property
    def is_complete(self):
        """Check if log totals equal 24 hours."""
        return abs(float(self.total_hours_sum) - 24.0) < 0.1
    
    def get_duty_status_summary(self):
        """Get summary of duty status hours."""
        return {
            'off_duty': float(self.total_hours_off_duty),
            'sleeper_berth': float(self.total_hours_sleeper_berth),
            'driving': float(self.total_hours_driving),
            'on_duty_not_driving': float(self.total_hours_on_duty_not_driving),
            'total': float(self.total_hours_sum),
            'is_complete': self.is_complete
        }
    
    def get_certification_status(self):
        """Get certification status information."""
        return {
            'is_certified': self.is_certified,
            'signature_date': self.driver_signature_date.isoformat() if self.driver_signature_date else None,
            'driver_name': self.driver_name
        }
    
    def certify_log(self):
        """Mark log as certified by driver."""
        self.is_certified = True
        self.driver_signature_date = timezone.now()
        self.save()
    
    def validate_compliance(self):
        """Validate log against HOS regulations."""
        violations = []
        
        # Check total hours add up to 24
        if not self.is_complete:
            violations.append({
                'type': 'incomplete_log',
                'description': f'Total hours ({self.total_hours_sum}) does not equal 24',
                'severity': 'error'
            })
        
        # Check driving time limit (11 hours)
        if self.total_hours_driving > 11:
            violations.append({
                'type': 'driving_limit_exceeded',
                'description': f'Driving time ({self.total_hours_driving}h) exceeds 11-hour limit',
                'severity': 'violation'
            })
        
        # Check minimum off-duty time
        total_rest = self.total_hours_off_duty + self.total_hours_sleeper_berth
        if total_rest < 10:
            violations.append({
                'type': 'insufficient_rest',
                'description': f'Total rest time ({total_rest}h) is less than 10 hours',
                'severity': 'violation'
            })
        
        return violations
