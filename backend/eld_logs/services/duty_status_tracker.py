"""
Duty Status Tracker Service.

Tracks and records duty status changes during trips for ELD compliance.
Manages the creation and sequencing of duty status records that form
the basis of daily logs as required by FMCSA regulations.

This service handles:
- Duty status change recording
- Location tracking for duty changes
- Duration calculations
- Sequence management
- Compliance validation

Single Responsibility: Duty status tracking and recording only.
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class DutyStatusTrackerService:
    """
    Service for tracking driver duty status changes during trips.

    Records all duty status changes with proper timing, location,
    and compliance validation for ELD requirements.
    """

    # Duty status options from HOS regulations
    DUTY_STATUS_CHOICES = [
        "off_duty",
        "sleeper_berth",
        "driving",
        "on_duty_not_driving",
    ]

    # Minimum duration for duty status records (15 minutes for ELD compliance)
    MIN_RECORD_DURATION_MINUTES = 15

    def __init__(self):
        """Initialize duty status tracker."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def start_trip_tracking(
        self,
        trip_id: str,
        driver_name: str,
        initial_status: str = "on_duty_not_driving",
        current_location: str = "",
        start_time: Optional[datetime] = None,
    ) -> Dict:
        """
        Start tracking duty status for a new trip.

        Args:
            trip_id: Unique identifier for the trip
            driver_name: Driver's full legal name
            initial_status: Initial duty status (default: on_duty_not_driving)
            current_location: Current location description
            start_time: Start time (default: now)

        Returns:
            Dict containing initial tracking status
        """
        try:
            if start_time is None:
                start_time = timezone.now()

            self.logger.info(
                f"Starting trip tracking for {driver_name} - Trip {trip_id}"
            )

            # Validate initial status
            if initial_status not in self.DUTY_STATUS_CHOICES:
                raise ValueError(f"Invalid duty status: {initial_status}")

            # Create initial duty status record
            initial_record = self._create_duty_status_record(
                trip_id=trip_id,
                duty_status=initial_status,
                start_time=start_time,
                location_description=current_location,
                sequence_order=1,
                remarks=f"Trip started - {driver_name}",
            )

            # Initialize tracking state
            tracking_state = {
                "trip_id": trip_id,
                "driver_name": driver_name,
                "current_status": initial_status,
                "status_start_time": start_time.isoformat(),
                "current_location": current_location,
                "last_record_id": initial_record["id"],
                "sequence_order": 1,
                "total_records": 1,
                "tracking_started_at": start_time.isoformat(),
            }

            self.logger.info(f"Trip tracking started successfully for trip {trip_id}")
            return tracking_state

        except Exception as e:
            self.logger.error(f"Failed to start trip tracking: {str(e)}")
            raise DutyStatusTrackingError(f"Failed to start trip tracking: {str(e)}")

    def record_status_change(
        self,
        trip_id: str,
        new_status: str,
        location_description: str = "",
        location_city: str = "",
        location_state: str = "",
        change_time: Optional[datetime] = None,
        remarks: str = "",
        miles_driven: Optional[Decimal] = None,
    ) -> Dict:
        """
        Record a duty status change.

        Args:
            trip_id: Trip identifier
            new_status: New duty status
            location_description: Location description for remarks
            location_city: City where change occurred
            location_state: State where change occurred (2-letter abbreviation)
            change_time: Time of change (default: now)
            remarks: Additional remarks
            miles_driven: Miles driven since last change (for driving status)

        Returns:
            Dict containing status change record information
        """
        try:
            if change_time is None:
                change_time = timezone.now()

            self.logger.debug(
                f"Recording status change to {new_status} for trip {trip_id}"
            )

            # Validate new status
            if new_status not in self.DUTY_STATUS_CHOICES:
                raise ValueError(f"Invalid duty status: {new_status}")

            # Get current tracking state
            current_state = self._get_current_tracking_state(trip_id)

            # Calculate duration of previous status
            previous_duration = self._calculate_status_duration(
                current_state["status_start_time"], change_time
            )

            # Update previous record with end time and duration
            self._finalize_previous_record(
                current_state["last_record_id"],
                change_time,
                previous_duration,
                miles_driven,
            )

            # Create new status record
            new_record = self._create_duty_status_record(
                trip_id=trip_id,
                duty_status=new_status,
                start_time=change_time,
                location_description=location_description,
                location_city=location_city,
                location_state=location_state,
                sequence_order=current_state["sequence_order"] + 1,
                remarks=remarks
                or self._generate_default_remarks(
                    new_status, location_city, location_state
                ),
            )

            # Update tracking state
            updated_state = {
                "trip_id": trip_id,
                "current_status": new_status,
                "status_start_time": change_time.isoformat(),
                "current_location": location_description
                or f"{location_city}, {location_state}",
                "last_record_id": new_record["id"],
                "sequence_order": current_state["sequence_order"] + 1,
                "total_records": current_state["total_records"] + 1,
                "previous_status": current_state["current_status"],
                "previous_duration_minutes": previous_duration,
                "change_recorded_at": change_time.isoformat(),
            }

            self.logger.info(
                f"Status change recorded: {current_state['current_status']} -> {new_status}"
            )
            return updated_state

        except Exception as e:
            self.logger.error(f"Failed to record status change: {str(e)}")
            raise DutyStatusTrackingError(f"Failed to record status change: {str(e)}")

    def end_trip_tracking(
        self,
        trip_id: str,
        end_time: Optional[datetime] = None,
        final_location: str = "",
        miles_driven: Optional[Decimal] = None,
    ) -> Dict:
        """
        End tracking for a trip and finalize all records.

        Args:
            trip_id: Trip identifier
            end_time: End time (default: now)
            final_location: Final location description
            miles_driven: Miles driven in final segment

        Returns:
            Dict containing trip tracking summary
        """
        try:
            if end_time is None:
                end_time = timezone.now()

            self.logger.info(f"Ending trip tracking for trip {trip_id}")

            # Get current tracking state
            current_state = self._get_current_tracking_state(trip_id)

            # Calculate final duration
            final_duration = self._calculate_status_duration(
                current_state["status_start_time"], end_time
            )

            # Finalize last record
            self._finalize_previous_record(
                current_state["last_record_id"], end_time, final_duration, miles_driven
            )

            # Generate trip summary
            trip_summary = self._generate_trip_tracking_summary(trip_id, end_time)

            self.logger.info(f"Trip tracking ended successfully for trip {trip_id}")
            return trip_summary

        except Exception as e:
            self.logger.error(f"Failed to end trip tracking: {str(e)}")
            raise DutyStatusTrackingError(f"Failed to end trip tracking: {str(e)}")

    def get_duty_status_records(
        self,
        trip_id: str,
        status_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get duty status records for a trip.

        Args:
            trip_id: Trip identifier
            status_filter: Optional status to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of duty status records
        """
        try:
            # This would query the DutyStatusRecord model
            # For now, return mock data structure
            records = self._get_records_from_database(
                trip_id, status_filter, start_time, end_time
            )

            return records

        except Exception as e:
            self.logger.error(f"Failed to get duty status records: {str(e)}")
            raise DutyStatusTrackingError(
                f"Failed to get duty status records: {str(e)}"
            )

    def validate_duty_status_sequence(self, trip_id: str) -> Dict:
        """
        Validate duty status record sequence for compliance.

        Args:
            trip_id: Trip identifier

        Returns:
            Dict containing validation results
        """
        try:
            records = self.get_duty_status_records(trip_id)

            violations = []
            warnings = []

            # Check for gaps in time coverage
            time_gaps = self._check_time_gaps(records)
            violations.extend(time_gaps)

            # Check minimum duration compliance
            short_records = self._check_minimum_durations(records)
            warnings.extend(short_records)

            # Check location information completeness
            missing_locations = self._check_location_completeness(records)
            warnings.extend(missing_locations)

            # Check driving time compliance
            driving_violations = self._check_driving_time_compliance(records)
            violations.extend(driving_violations)

            is_valid = len(violations) == 0

            return {
                "is_valid": is_valid,
                "violations": violations,
                "warnings": warnings,
                "total_records": len(records),
                "validation_score": self._calculate_validation_score(
                    violations, warnings
                ),
                "validated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Failed to validate duty status sequence: {str(e)}")
            raise DutyStatusTrackingError(
                f"Failed to validate duty status sequence: {str(e)}"
            )

    def _create_duty_status_record(
        self,
        trip_id: str,
        duty_status: str,
        start_time: datetime,
        location_description: str = "",
        location_city: str = "",
        location_state: str = "",
        sequence_order: int = 1,
        remarks: str = "",
    ) -> Dict:
        """Create a new duty status record."""
        # This would create a DutyStatusRecord model instance
        # For now, return mock record structure
        record_id = f"record_{trip_id}_{sequence_order}"

        record = {
            "id": record_id,
            "trip_id": trip_id,
            "duty_status": duty_status,
            "start_time": start_time.isoformat(),
            "end_time": None,  # Will be set when status changes
            "duration_minutes": 0,  # Will be calculated when finalized
            "location_description": location_description,
            "location_city": location_city,
            "location_state": location_state,
            "sequence_order": sequence_order,
            "remarks": remarks,
            "miles_driven": None,
            "created_at": timezone.now().isoformat(),
        }

        self.logger.debug(f"Created duty status record: {record_id}")
        return record

    def _finalize_previous_record(
        self,
        record_id: str,
        end_time: datetime,
        duration_minutes: int,
        miles_driven: Optional[Decimal] = None,
    ):
        """Finalize a duty status record with end time and duration."""
        # This would update the DutyStatusRecord model instance
        self.logger.debug(
            f"Finalizing record {record_id} with {duration_minutes} minutes"
        )

        # Mock implementation - in real code this would update the database
        pass

    def _get_current_tracking_state(self, trip_id: str) -> Dict:
        """Get current tracking state for a trip."""
        # This would query the current state from database
        # For now, return mock state
        return {
            "trip_id": trip_id,
            "current_status": "driving",
            "status_start_time": (timezone.now() - timedelta(hours=2)).isoformat(),
            "current_location": "Highway 95, NV",
            "last_record_id": f"record_{trip_id}_2",
            "sequence_order": 2,
            "total_records": 2,
        }

    def _calculate_status_duration(
        self, start_time_str: str, end_time: datetime
    ) -> int:
        """Calculate duration between start and end time in minutes."""
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        if start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)

        duration = end_time - start_time
        minutes = int(duration.total_seconds() / 60)

        # Round to nearest 15 minutes for ELD compliance
        rounded_minutes = (
            round(minutes / self.MIN_RECORD_DURATION_MINUTES)
            * self.MIN_RECORD_DURATION_MINUTES
        )
        return max(self.MIN_RECORD_DURATION_MINUTES, rounded_minutes)

    def _generate_default_remarks(
        self, duty_status: str, city: str = "", state: str = ""
    ) -> str:
        """Generate default remarks for duty status change."""
        location = f"{city}, {state}" if city and state else "Location not specified"

        status_descriptions = {
            "off_duty": f"Off duty - {location}",
            "sleeper_berth": f"Sleeper berth - {location}",
            "driving": f"Driving from {location}",
            "on_duty_not_driving": f"On duty (not driving) - {location}",
        }

        return status_descriptions.get(duty_status, f"Status change - {location}")

    def _generate_trip_tracking_summary(self, trip_id: str, end_time: datetime) -> Dict:
        """Generate comprehensive trip tracking summary."""
        records = self.get_duty_status_records(trip_id)

        # Calculate totals by duty status
        status_totals = {
            "off_duty": 0,
            "sleeper_berth": 0,
            "driving": 0,
            "on_duty_not_driving": 0,
        }

        total_miles = Decimal("0")

        for record in records:
            status = record["duty_status"]
            duration = record.get("duration_minutes", 0)
            status_totals[status] += duration

            if record.get("miles_driven"):
                total_miles += Decimal(str(record["miles_driven"]))

        # Convert minutes to hours
        status_hours = {
            status: round(minutes / 60, 2) for status, minutes in status_totals.items()
        }

        return {
            "trip_id": trip_id,
            "tracking_ended_at": end_time.isoformat(),
            "total_records": len(records),
            "total_miles_driven": float(total_miles),
            "status_hours": status_hours,
            "status_minutes": status_totals,
            "total_hours": sum(status_hours.values()),
            "driving_hours": status_hours["driving"],
            "on_duty_hours": status_hours["driving"]
            + status_hours["on_duty_not_driving"],
            "off_duty_hours": status_hours["off_duty"] + status_hours["sleeper_berth"],
        }

    def _get_records_from_database(
        self,
        trip_id: str,
        status_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get duty status records from database."""
        # Mock implementation - in real code this would query DutyStatusRecord model
        return [
            {
                "id": f"record_{trip_id}_1",
                "trip_id": trip_id,
                "duty_status": "on_duty_not_driving",
                "start_time": (timezone.now() - timedelta(hours=3)).isoformat(),
                "end_time": (timezone.now() - timedelta(hours=2)).isoformat(),
                "duration_minutes": 60,
                "location_city": "Las Vegas",
                "location_state": "NV",
                "sequence_order": 1,
                "remarks": "Trip preparation",
                "miles_driven": None,
            },
            {
                "id": f"record_{trip_id}_2",
                "trip_id": trip_id,
                "duty_status": "driving",
                "start_time": (timezone.now() - timedelta(hours=2)).isoformat(),
                "end_time": timezone.now().isoformat(),
                "duration_minutes": 120,
                "location_city": "Barstow",
                "location_state": "CA",
                "sequence_order": 2,
                "remarks": "Driving to destination",
                "miles_driven": Decimal("110"),
            },
        ]

    def _check_time_gaps(self, records: List[Dict]) -> List[Dict]:
        """Check for gaps in time coverage."""
        violations = []

        sorted_records = sorted(records, key=lambda x: x["sequence_order"])

        for i in range(len(sorted_records) - 1):
            current_end = datetime.fromisoformat(
                sorted_records[i]["end_time"].replace("Z", "+00:00")
            )
            next_start = datetime.fromisoformat(
                sorted_records[i + 1]["start_time"].replace("Z", "+00:00")
            )

            if next_start > current_end:
                gap_minutes = (next_start - current_end).total_seconds() / 60
                violations.append(
                    {
                        "type": "time_gap",
                        "description": f"Gap of {gap_minutes:.0f} minutes between records",
                        "gap_minutes": gap_minutes,
                        "between_records": [
                            sorted_records[i]["id"],
                            sorted_records[i + 1]["id"],
                        ],
                    }
                )

        return violations

    def _check_minimum_durations(self, records: List[Dict]) -> List[Dict]:
        """Check for records below minimum duration."""
        warnings = []

        for record in records:
            if record["duration_minutes"] < self.MIN_RECORD_DURATION_MINUTES:
                warnings.append(
                    {
                        "type": "short_duration",
                        "description": f'Record duration ({record["duration_minutes"]} min) below minimum ({self.MIN_RECORD_DURATION_MINUTES} min)',
                        "record_id": record["id"],
                        "duration_minutes": record["duration_minutes"],
                    }
                )

        return warnings

    def _check_location_completeness(self, records: List[Dict]) -> List[Dict]:
        """Check for missing location information."""
        warnings = []

        for record in records:
            if not record.get("location_city") or not record.get("location_state"):
                warnings.append(
                    {
                        "type": "missing_location",
                        "description": "Record missing city/state location information",
                        "record_id": record["id"],
                        "duty_status": record["duty_status"],
                    }
                )

        return warnings

    def _check_driving_time_compliance(self, records: List[Dict]) -> List[Dict]:
        """Check driving time compliance with HOS regulations."""
        violations = []

        # Check for continuous driving over 8 hours without 30-min break
        continuous_driving_minutes = 0

        for record in sorted(records, key=lambda x: x["sequence_order"]):
            if record["duty_status"] == "driving":
                continuous_driving_minutes += record["duration_minutes"]

                if continuous_driving_minutes > 480:  # 8 hours = 480 minutes
                    violations.append(
                        {
                            "type": "driving_time_violation",
                            "description": "Continuous driving exceeds 8 hours without 30-minute break",
                            "continuous_minutes": continuous_driving_minutes,
                            "record_id": record["id"],
                        }
                    )

            elif record["duration_minutes"] >= 30:  # 30-minute break
                continuous_driving_minutes = 0

        return violations

    def _calculate_validation_score(
        self, violations: List[Dict], warnings: List[Dict]
    ) -> int:
        """Calculate validation score (0-100)."""
        score = 100
        score -= len(violations) * 20  # Each violation: -20 points
        score -= len(warnings) * 5  # Each warning: -5 points
        return max(0, min(100, score))


    def create_duty_status_record(
        self, 
        daily_log, 
        duty_status, 
        change_time, 
        location, 
        odometer_reading=None, 
        engine_hours=None, 
        remarks=''
    ):
        """
        Create a duty status record for a daily log (API compatibility method).
        
        Args:
            daily_log: DailyLog instance
            duty_status: New duty status
            change_time: Time of change
            location: Location description
            odometer_reading: Optional odometer reading
            engine_hours: Optional engine hours
            remarks: Additional remarks
            
        Returns:
            Created DutyStatusRecord instance
        """
        try:
            from ..models import DutyStatusRecord
            
            # Parse location to get city and state
            location_city, location_state = self._parse_location_string(location)
            
            # Get next sequence number
            next_sequence = daily_log.duty_status_records.count() + 1
            
            # Create the record
            record = DutyStatusRecord.objects.create(
                daily_log=daily_log,
                duty_status=duty_status,
                start_time=change_time,
                location_city=location_city,
                location_state=location_state,
                location_description=location,
                odometer_reading=odometer_reading,
                engine_hours=engine_hours,
                remarks=remarks or self._generate_default_remarks(duty_status, location_city, location_state),
                sequence_order=next_sequence,
                record_type='manual'
            )
            
            self.logger.info(f"Created duty status record {record.id} for daily log {daily_log.id}")
            return record
            
        except Exception as e:
            self.logger.error(f"Failed to create duty status record: {str(e)}")
            raise DutyStatusTrackingError(f"Failed to create duty status record: {str(e)}")
    
    def _parse_location_string(self, location: str) -> tuple[str, str]:
        """
        Parse location string to extract city and state.
        
        Args:
            location: Location string to parse
            
        Returns:
            Tuple of (city, state)
        """
        if not location:
            return "", ""
        
        # Try to extract city, state from common patterns
        if "," in location:
            parts = location.split(",")
            if len(parts) >= 2:
                city = parts[0].strip()
                state = parts[1].strip()
                # Extract state abbreviation if it looks like one
                state_parts = state.split()
                if state_parts and len(state_parts[-1]) == 2:
                    return city, state_parts[-1].upper()
                return city, state[:2].upper() if len(state) >= 2 else state
        
        return location[:50], ""  # Return as city if can't parse


class DutyStatusTrackingError(Exception):
    """Exception raised when duty status tracking fails."""

    pass
