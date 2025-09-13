"""
Duty Status Record model for ELD compliance.

Contains the DutyStatusRecord model that tracks individual duty status
changes with location information as required for ELD compliance.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class DutyStatusRecord(models.Model):
    """
    Individual duty status change record.

    Each record represents a change in duty status with location information
    as required for ELD compliance. These records make up the detailed
    entries that support the daily log totals.

    Attributes:
        id: UUID primary key
        daily_log: Foreign key to DailyLog
        duty_status: Current duty status (off_duty, sleeper_berth, driving, on_duty_not_driving)
        start_time: When this duty status period started
        end_time: When this duty status period ended
        duration_minutes: Duration of this duty status in minutes
        location_city: City where duty status changed
        location_state: State where duty status changed
        location_description: Location description
        latitude/longitude: GPS coordinates (optional)
        remarks: Additional remarks for this duty status change
        odometer_reading: Vehicle odometer reading at status change
        miles_driven_this_period: Miles driven during this duty status period
        sequence_order: Order of this record within the daily log
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the duty status record",
    )

    # Link to daily log
    daily_log = models.ForeignKey(
        "eld_logs.DailyLog",
        on_delete=models.CASCADE,
        related_name="duty_status_records",
        help_text="The daily log this record belongs to",
    )

    # Duty status (matches grid rows on log sheet)
    class DutyStatus(models.TextChoices):
        OFF_DUTY = "off_duty", "Off Duty"
        SLEEPER_BERTH = "sleeper_berth", "Sleeper Berth"
        DRIVING = "driving", "Driving"
        ON_DUTY_NOT_DRIVING = "on_duty_not_driving", "On Duty (Not Driving)"

    duty_status = models.CharField(
        max_length=20,
        choices=DutyStatus.choices,
        help_text="Duty status for this time period",
    )

    # Time range for this duty status
    start_time = models.DateTimeField(help_text="When this duty status period started")

    end_time = models.DateTimeField(
        null=True, blank=True, help_text="When this duty status period ended"
    )

    duration_minutes = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Duration of this duty status in minutes",
    )

    # Location information (required in remarks for ELD compliance)
    location_city = models.CharField(
        max_length=100, blank=True, help_text="City where duty status changed"
    )

    location_state = models.CharField(
        max_length=50,
        blank=True,
        help_text="State where duty status changed (2-letter abbreviation preferred)",
    )

    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location description (e.g., 'I-95 Mile 45', 'Rest Area', 'Customer Site')",
    )

    # GPS coordinates (optional but helpful for ELD compliance)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Latitude where duty status changed (-90 to 90)",
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Longitude where duty status changed (-180 to 180)",
    )

    # Additional context
    remarks = models.CharField(
        max_length=200,
        blank=True,
        help_text="Additional remarks for this duty status change",
    )

    # Mileage information (important for driving records)
    odometer_reading = models.PositiveIntegerField(
        null=True, blank=True, help_text="Vehicle odometer reading at status change"
    )

    miles_driven_this_period = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Miles driven during this duty status period",
    )

    # Sequence order within the daily log
    sequence_order = models.PositiveIntegerField(
        help_text="Order of this record within the daily log (0-based)"
    )

    # Record type (automatic vs manual entry)
    class RecordType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic (ELD Generated)"
        MANUAL = "manual", "Manual Entry"
        ASSUMED = "assumed", "Assumed (Gap Filling)"
        EDITED = "edited", "Edited Record"

    record_type = models.CharField(
        max_length=10,
        choices=RecordType.choices,
        default=RecordType.MANUAL,
        help_text="How this record was created",
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this record was last updated"
    )

    class Meta:
        db_table = "eld_logs_dutystatusrecord"
        ordering = ["daily_log", "sequence_order"]
        unique_together = ["daily_log", "sequence_order"]
        verbose_name = "Duty Status Record"
        verbose_name_plural = "Duty Status Records"
        indexes = [
            models.Index(fields=["daily_log", "sequence_order"]),
            models.Index(fields=["duty_status"]),
            models.Index(fields=["start_time"]),
        ]

    def __str__(self):
        """Return string representation of the duty status record."""
        return f"{self.get_duty_status_display()} from {self.start_time.strftime('%H:%M')} ({self.duration_minutes}min)"

    def save(self, *args, **kwargs):
        """Override save to validate and calculate duration."""
        # Validate coordinates if provided
        if self.latitude is not None:
            if not (-90 <= float(self.latitude) <= 90):
                raise ValueError("Latitude must be between -90 and 90 degrees")
        if self.longitude is not None:
            if not (-180 <= float(self.longitude) <= 180):
                raise ValueError("Longitude must be between -180 and 180 degrees")

        # Calculate duration if start and end times are provided
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)

        super().save(*args, **kwargs)

    @property
    def duration_hours(self):
        """Return duration in hours."""
        return round(self.duration_minutes / 60, 2)

    @property
    def location_for_remarks(self):
        """Format location for remarks section per ELD requirements."""
        if self.location_city and self.location_state:
            return f"{self.location_city}, {self.location_state}"
        elif self.location_description:
            return self.location_description
        elif self.latitude and self.longitude:
            return f"GPS: {self.latitude:.4f}, {self.longitude:.4f}"
        else:
            return "Location not specified"

    def get_full_location_string(self):
        """Get complete location string for ELD compliance."""
        parts = []

        if self.location_city and self.location_state:
            parts.append(f"{self.location_city}, {self.location_state}")
        elif self.location_description:
            parts.append(self.location_description)

        if self.latitude and self.longitude:
            parts.append(f"GPS: {self.latitude:.6f}, {self.longitude:.6f}")

        return "; ".join(parts) if parts else "Location not specified"

    def is_driving_record(self):
        """Check if this is a driving duty status record."""
        return self.duty_status == self.DutyStatus.DRIVING

    def is_rest_record(self):
        """Check if this is a rest/off-duty record."""
        return self.duty_status in [
            self.DutyStatus.OFF_DUTY,
            self.DutyStatus.SLEEPER_BERTH,
        ]

    def get_time_range_display(self):
        """Get formatted time range for display."""
        start = self.start_time.strftime("%H:%M")
        if self.end_time:
            end = self.end_time.strftime("%H:%M")
            return f"{start} - {end}"
        return f"{start} - ongoing"

    def calculate_average_speed_mph(self):
        """Calculate average speed during this period if driving."""
        if (
            self.is_driving_record()
            and self.miles_driven_this_period > 0
            and self.duration_minutes > 0
        ):

            hours = self.duration_minutes / 60
            return round(float(self.miles_driven_this_period) / hours, 1)
        return 0

    def validate_record(self):
        """Validate this duty status record."""
        errors = []

        if self.duration_minutes < 0:
            errors.append("Duration cannot be negative")

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors.append("Start time must be before end time")

        if self.is_driving_record():
            if self.miles_driven_this_period < 0:
                errors.append("Miles driven cannot be negative")

            # Check for reasonable average speed
            avg_speed = self.calculate_average_speed_mph()
            if avg_speed > 80:
                errors.append(f"Average speed {avg_speed} mph seems too high")
            elif avg_speed > 0 and avg_speed < 5:
                errors.append(
                    f"Average speed {avg_speed} mph seems too low for driving"
                )

        else:
            # Non-driving records should not have miles
            if self.miles_driven_this_period > 0:
                errors.append("Non-driving records should not have miles driven")

        return errors

    def get_record_summary(self):
        """Get summary information for this record."""
        return {
            "duty_status": self.duty_status,
            "duty_status_display": self.get_duty_status_display(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "duration_hours": self.duration_hours,
            "location": self.location_for_remarks,
            "miles_driven": float(self.miles_driven_this_period),
            "average_speed_mph": self.calculate_average_speed_mph(),
            "sequence_order": self.sequence_order,
            "record_type": self.record_type,
        }
