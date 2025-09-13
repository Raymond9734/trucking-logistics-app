"""
Compliance Violation model for HOS compliance.

Contains the ComplianceViolation model that tracks potential
and actual HOS violations.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class ComplianceViolation(models.Model):
    """
    Track potential or actual HOS violations.
    
    Used for monitoring and preventing violations before they occur.
    This model helps with compliance management and reporting.
    
    Attributes:
        id: UUID primary key
        trip: Foreign key to Trip
        violation_type: Type of HOS violation
        severity: Severity level (warning, violation, critical)
        description: Description of the violation or risk
        current_value: Current value (e.g., hours driven)
        limit_value: Regulatory limit value
        is_resolved: Whether the violation has been resolved
        resolution_notes: Notes on how violation was resolved
        detected_at: When violation was detected
        resolved_at: When violation was resolved
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the compliance violation"
    )
    
    # Link to trip
    trip = models.ForeignKey(
        'routes.Trip',
        on_delete=models.CASCADE,
        related_name='compliance_violations',
        help_text="The trip this violation relates to"
    )
    
    # Violation type classification
    class ViolationType(models.TextChoices):
        CYCLE_LIMIT = 'cycle_limit', '70-Hour/8-Day Cycle Limit'
        DUTY_PERIOD = 'duty_period', '14-Hour Duty Period Limit'
        DRIVING_LIMIT = 'driving_limit', '11-Hour Driving Limit'
        REST_BREAK = 'rest_break', '30-Minute Rest Break Required'
        OFF_DUTY = 'off_duty', '10-Hour Off Duty Required'
        SLEEPER_BERTH = 'sleeper_berth', 'Sleeper Berth Provision Violation'
        RECORD_KEEPING = 'record_keeping', 'Record Keeping Violation'
        FALSE_LOG = 'false_log', 'False Log Entry'
    
    violation_type = models.CharField(
        max_length=20,
        choices=ViolationType.choices,
        help_text="Type of HOS violation"
    )
    
    # Severity levels
    class Severity(models.TextChoices):
        WARNING = 'warning', 'Warning (Approaching Limit)'
        VIOLATION = 'violation', 'Violation (Limit Exceeded)'
        CRITICAL = 'critical', 'Critical (Safety Risk)'
        IMMINENT = 'imminent', 'Imminent Violation Risk'
    
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.WARNING,
        help_text="Severity level of the violation"
    )
    
    # Violation details
    description = models.CharField(
        max_length=200,
        help_text="Description of the violation or risk"
    )
    
    current_value = models.DecimalField(
        max_digits=5, 
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text="Current value (e.g., hours driven)"
    )
    
    limit_value = models.DecimalField(
        max_digits=5, 
        decimal_places=1,
        validators=[MinValueValidator(0)],
        help_text="Regulatory limit value"
    )
    
    # Regulatory reference
    regulation_reference = models.CharField(
        max_length=50,
        blank=True,
        help_text="FMCSA regulation reference (e.g., '395.3(a)(2)')"
    )
    
    # Location where violation occurred/detected
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location where violation occurred or was detected"
    )
    
    # Resolution tracking
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether the violation has been resolved"
    )
    
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notes on how the violation was resolved"
    )
    
    # Resolution method
    class ResolutionMethod(models.TextChoices):
        REST_BREAK = 'rest_break', 'Took Required Rest Break'
        ROUTE_CHANGE = 'route_change', 'Changed Route'
        SCHEDULE_CHANGE = 'schedule_change', 'Changed Schedule'
        DRIVER_CHANGE = 'driver_change', 'Changed Driver'
        CANCELLED_TRIP = 'cancelled_trip', 'Cancelled Trip'
        LOG_CORRECTION = 'log_correction', 'Corrected Log Entry'
        OTHER = 'other', 'Other Method'
    
    resolution_method = models.CharField(
        max_length=20,
        choices=ResolutionMethod.choices,
        blank=True,
        help_text="Method used to resolve the violation"
    )
    
    # Impact assessment
    class Impact(models.TextChoices):
        LOW = 'low', 'Low Impact'
        MEDIUM = 'medium', 'Medium Impact'
        HIGH = 'high', 'High Impact'
        SAFETY_RISK = 'safety_risk', 'Safety Risk'
    
    impact = models.CharField(
        max_length=20,
        choices=Impact.choices,
        default=Impact.MEDIUM,
        help_text="Impact level of the violation"
    )
    
    # Prevention flag
    was_prevented = models.BooleanField(
        default=False,
        help_text="Whether this violation was prevented before occurring"
    )
    
    # Timestamps
    detected_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the violation was detected"
    )
    
    resolved_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the violation was resolved"
    )
    
    # Follow-up required
    requires_follow_up = models.BooleanField(
        default=False,
        help_text="Whether this violation requires follow-up action"
    )
    
    follow_up_notes = models.TextField(
        blank=True,
        help_text="Notes on required follow-up actions"
    )
    
    class Meta:
        db_table = 'hos_compliance_violation'
        ordering = ['-detected_at']
        verbose_name = 'Compliance Violation'
        verbose_name_plural = 'Compliance Violations'
        indexes = [
            models.Index(fields=['trip', 'violation_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['detected_at']),
        ]
    
    def __str__(self):
        """Return string representation of the violation."""
        return f"{self.get_violation_type_display()} - {self.get_severity_display()} for {self.trip.driver_name}"
    
    @property
    def hours_over_limit(self):
        """Calculate how many hours over the limit."""
        return max(0, float(self.current_value - self.limit_value))
    
    @property
    def hours_until_limit(self):
        """Calculate hours until reaching the limit."""
        return max(0, float(self.limit_value - self.current_value))
    
    @property
    def resolution_time_hours(self):
        """Calculate how long it took to resolve the violation."""
        if self.resolved_at and self.detected_at:
            delta = self.resolved_at - self.detected_at
            return round(delta.total_seconds() / 3600, 1)
        return None
    
    def get_violation_category(self):
        """Get the category of violation for reporting purposes."""
        categories = {
            self.ViolationType.CYCLE_LIMIT: "Hours of Service",
            self.ViolationType.DUTY_PERIOD: "Hours of Service", 
            self.ViolationType.DRIVING_LIMIT: "Hours of Service",
            self.ViolationType.REST_BREAK: "Hours of Service",
            self.ViolationType.OFF_DUTY: "Hours of Service",
            self.ViolationType.SLEEPER_BERTH: "Hours of Service",
            self.ViolationType.RECORD_KEEPING: "Record Keeping",
            self.ViolationType.FALSE_LOG: "Record Keeping",
        }
        return categories.get(self.violation_type, "Other")
    
    def get_recommended_actions(self):
        """Get recommended actions to resolve this violation."""
        actions = {
            self.ViolationType.CYCLE_LIMIT: [
                "Take 34-hour restart",
                "Wait for hours to roll off 8-day window",
                "Transfer load to another driver"
            ],
            self.ViolationType.DUTY_PERIOD: [
                "Take 10 consecutive hours off duty",
                "Use sleeper berth provision if equipped"
            ],
            self.ViolationType.DRIVING_LIMIT: [
                "Take 10 consecutive hours off duty",
                "Use sleeper berth provision if equipped"
            ],
            self.ViolationType.REST_BREAK: [
                "Take 30-minute consecutive break",
                "Combine with other required stops"
            ],
            self.ViolationType.OFF_DUTY: [
                "Complete required off-duty period",
                "Find safe parking location"
            ],
        }
        return actions.get(self.violation_type, ["Consult HOS regulations", "Contact safety department"])
    
    def mark_resolved(self, method=None, notes=""):
        """Mark violation as resolved with optional method and notes."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if method:
            self.resolution_method = method
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def is_critical_violation(self):
        """Check if this is a critical safety violation."""
        return self.severity in [self.Severity.CRITICAL, self.Severity.IMMINENT] or \
               self.impact == self.Impact.SAFETY_RISK
    
    def get_violation_severity_color(self):
        """Get color code for violation severity (for UI display)."""
        colors = {
            self.Severity.WARNING: "#FFA500",  # Orange
            self.Severity.VIOLATION: "#FF0000",  # Red
            self.Severity.CRITICAL: "#8B0000",  # Dark Red
            self.Severity.IMMINENT: "#DC143C",  # Crimson
        }
        return colors.get(self.severity, "#808080")  # Gray default
