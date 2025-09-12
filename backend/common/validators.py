"""
Common validators and utilities for the trucking logistics application.

This module contains shared validation logic and utility functions used
across multiple Django apps.
"""

from decimal import Decimal
from django.core.validators import BaseValidator


class GPSCoordinateValidator(BaseValidator):
    """
    Validator for GPS coordinates (latitude/longitude).

    Ensures coordinates are within valid ranges:
    - Latitude: -90 to 90 degrees
    - Longitude: -180 to 180 degrees
    """

    def __init__(self, coordinate_type="latitude"):
        self.coordinate_type = coordinate_type

        if coordinate_type == "latitude":
            self.limit_value = (-90, 90)
            self.message = "Latitude must be between -90 and 90 degrees."
        elif coordinate_type == "longitude":
            self.limit_value = (-180, 180)
            self.message = "Longitude must be between -180 and 180 degrees."
        else:
            raise ValueError("coordinate_type must be 'latitude' or 'longitude'")

    def compare(self, value, limit_value):
        min_val, max_val = limit_value
        return not (min_val <= float(value) <= max_val)

    def clean(self, value):
        return float(value)


def validate_latitude(value):
    """Validate latitude coordinate."""
    validator = GPSCoordinateValidator("latitude")
    validator(value)


def validate_longitude(value):
    """Validate longitude coordinate."""
    validator = GPSCoordinateValidator("longitude")
    validator(value)


class HoursValidator(BaseValidator):
    """
    Validator for hours values in HOS context.

    Ensures hours are positive and within reasonable limits.
    """

    def __init__(self, max_hours=24, allow_decimal=True):
        self.limit_value = max_hours
        self.allow_decimal = allow_decimal
        self.message = f"Hours must be between 0 and {max_hours}."

    def compare(self, value, limit_value):
        try:
            hours = float(value)
            return not (0 <= hours <= limit_value)
        except (ValueError, TypeError):
            return True

    def clean(self, value):
        if self.allow_decimal:
            return Decimal(str(value))
        else:
            return int(value)


def validate_driving_hours(value):
    """Validate driving hours (max 11 per FMCSA regulations)."""
    validator = HoursValidator(max_hours=11)
    validator(value)


def validate_duty_hours(value):
    """Validate duty period hours (max 14 per FMCSA regulations)."""
    validator = HoursValidator(max_hours=14)
    validator(value)


def validate_cycle_hours(value):
    """Validate cycle hours (max 70 per FMCSA regulations)."""
    validator = HoursValidator(max_hours=70)
    validator(value)


def calculate_distance_miles(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).

    Returns distance in miles.
    """
    from math import radians, cos, sin, asin, sqrt

    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Radius of earth in miles
    r = 3956

    return c * r


def format_duration_for_eld(minutes):
    """
    Format duration in minutes to HOS-compliant format.

    ELD regulations require time to be recorded in 15-minute increments.
    """
    # Round to nearest 15 minutes
    rounded_minutes = round(minutes / 15) * 15

    hours = rounded_minutes // 60
    mins = rounded_minutes % 60

    return f"{hours:02d}:{mins:02d}"


def get_fuel_stop_interval_miles():
    """
    Get fuel stop interval from project assumptions.

    Assessment specifies fueling at least once every 1,000 miles.
    """
    return 1000


def get_pickup_dropoff_duration_hours():
    """
    Get pickup/dropoff duration from project assumptions.

    Assessment specifies 1 hour for pickup and drop-off.
    """
    return 1.0


class HOSCalculator:
    """
    Utility class for HOS calculations based on FMCSA regulations.

    Implements the business logic for 70hr/8day, 14hr window, and 11hr driving limits.
    """

    @staticmethod
    def calculate_available_driving_hours(
        current_cycle_hours,
        current_duty_hours,
        current_driving_hours,
        hours_since_break=0,
    ):
        """
        Calculate available driving hours considering all HOS limits.

        Returns the minimum of all applicable limits.
        """
        # 70-hour/8-day limit
        cycle_available = max(0, 70 - current_cycle_hours)

        # 14-hour duty period limit
        duty_available = max(0, 14 - current_duty_hours)

        # 11-hour driving limit
        driving_available = max(0, 11 - current_driving_hours)

        # 30-minute break requirement (8 hours max continuous driving)
        break_available = max(0, 8 - hours_since_break) if hours_since_break < 8 else 0

        return min(
            cycle_available,
            duty_available,
            driving_available,
            break_available or float("inf"),
        )

    @staticmethod
    def requires_30_minute_break(hours_since_break):
        """Check if 30-minute break is required."""
        return hours_since_break >= 8

    @staticmethod
    def requires_10_hour_break(current_duty_hours):
        """Check if 10-hour off-duty break is required."""
        return current_duty_hours >= 14

    @staticmethod
    def get_next_required_break_type(
        current_cycle_hours,
        current_duty_hours,
        current_driving_hours,
        hours_since_break,
    ):
        """
        Determine what type of break is required next.

        Returns tuple: (break_type, duration_hours, reason)
        """

        if HOSCalculator.requires_30_minute_break(hours_since_break):
            return (
                "30_minute",
                0.5,
                "30-minute rest break required after 8 hours driving",
            )

        if current_driving_hours >= 11:
            return (
                "10_hour",
                10,
                "11-hour driving limit reached - 10 hours off duty required",
            )

        if current_duty_hours >= 14:
            return (
                "10_hour",
                10,
                "14-hour duty period limit reached - 10 hours off duty required",
            )

        if current_cycle_hours >= 70:
            return (
                "34_hour",
                34,
                "70-hour/8-day limit reached - 34-hour restart required",
            )

        return (None, 0, "No break currently required")


def validate_trip_locations(current_location, pickup_location, dropoff_location):
    """
    Validate that trip locations are provided and different.

    Returns list of validation errors.
    """
    errors = []

    if not current_location or not current_location.strip():
        errors.append("Current location is required")

    if not pickup_location or not pickup_location.strip():
        errors.append("Pickup location is required")

    if not dropoff_location or not dropoff_location.strip():
        errors.append("Dropoff location is required")

    # Check if locations are different (basic validation)
    locations = [
        current_location.strip().lower() if current_location else "",
        pickup_location.strip().lower() if pickup_location else "",
        dropoff_location.strip().lower() if dropoff_location else "",
    ]

    if len(set(locations)) < 3 and all(locations):
        errors.append("Trip locations should be different from each other")

    return errors
