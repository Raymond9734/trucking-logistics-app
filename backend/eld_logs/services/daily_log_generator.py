"""
Daily Log Generator Service for ELD compliance.

Generates compliant daily log sheets from trip data, including duty status records
and all required fields per FMCSA regulations. Handles multi-day trips and
automatic duty status tracking based on trip timeline.
"""

import logging
from datetime import datetime, timedelta, time
from decimal import Decimal
from typing import List, Dict, Optional
from django.db import transaction
from django.utils import timezone
from ..models import DailyLog, DutyStatusRecord
from hos_compliance.models import RestBreak

logger = logging.getLogger(__name__)


class DailyLogGeneratorService:
    """
    Service for generating ELD-compliant daily logs from trip data.

    Takes trip information and generates the required daily log sheets
    with duty status records, location information, and all compliance
    fields as required by FMCSA regulations.

    Single Responsibility: Daily log generation and ELD compliance
    """

    def __init__(self):
        """Initialize daily log generator service."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate_trip_daily_logs(self, trip) -> List[DailyLog]:
        """
        Generate daily logs for a complete trip.

        This is the main entry point called by TripPlannerService.

        Args:
            trip: Trip model instance with route and compliance info

        Returns:
            List of DailyLog instances covering the trip duration
        """
        try:
            with transaction.atomic():
                self.logger.info(f"Generating daily logs for trip {trip.id}")

                # Calculate trip timeline and duration
                trip_timeline = self._calculate_trip_timeline(trip)

                # Determine how many daily logs are needed
                daily_log_dates = self._determine_daily_log_dates(trip_timeline)

                # Generate daily logs for each date
                daily_logs = []
                for log_date in daily_log_dates:
                    daily_log = self._create_daily_log_for_date(trip, log_date, trip_timeline)
                    daily_logs.append(daily_log)

                self.logger.info(f"Generated {len(daily_logs)} daily logs for trip {trip.id}")
                return daily_logs

        except Exception as e:
            self.logger.error(f"Failed to generate daily logs for trip {trip.id}: {str(e)}")
            raise DailyLogGenerationError(f"Failed to generate daily logs: {str(e)}")

    def _calculate_trip_timeline(self, trip) -> Dict:
        """Calculate detailed timeline of trip activities."""
        try:
            timeline = {
                'trip_start_time': timezone.now(),
                'trip_end_time': None,
                'activities': [],
                'total_driving_hours': 0,
                'total_trip_hours': 0,
                'requires_rest_break': False
            }

            # Start with trip preparation (on-duty not driving)
            current_time = timeline['trip_start_time']
            activities = []

            # 1. Trip preparation (1 hour default)
            activities.append({
                'type': 'on_duty_not_driving',
                'start_time': current_time,
                'duration_minutes': 60,  # 1 hour prep time
                'location': trip.current_location,
                'description': 'Trip preparation and pre-trip inspection',
                'miles_driven': Decimal('0')
            })
            current_time += timedelta(hours=1)

            # 2. Driving from current to pickup location
            if hasattr(trip, 'route') and trip.route:
                route = trip.route
                waypoints = route.waypoints.all().order_by('sequence_order')
                
                for waypoint in waypoints:
                    if waypoint.estimated_time_from_previous_minutes > 0:
                        # Add driving segment
                        driving_minutes = waypoint.estimated_time_from_previous_minutes
                        activities.append({
                            'type': 'driving',
                            'start_time': current_time,
                            'duration_minutes': driving_minutes,
                            'location': waypoint.address,
                            'description': f'Driving to {waypoint.get_stop_type_display_name()}',
                            'miles_driven': waypoint.distance_from_previous_miles
                        })
                        current_time += timedelta(minutes=driving_minutes)
                        timeline['total_driving_hours'] += driving_minutes / 60

                    # Add stop/rest if applicable
                    if waypoint.estimated_stop_duration_minutes > 0:
                        stop_type = 'on_duty_not_driving' if waypoint.waypoint_type in ['pickup', 'delivery'] else 'off_duty'
                        activities.append({
                            'type': stop_type,
                            'start_time': current_time,
                            'duration_minutes': waypoint.estimated_stop_duration_minutes,
                            'location': waypoint.address,
                            'description': waypoint.stop_reason or f'{waypoint.get_stop_type_display_name()} stop',
                            'miles_driven': Decimal('0')
                        })
                        current_time += timedelta(minutes=waypoint.estimated_stop_duration_minutes)

            else:
                # Simple case: direct drive using estimated driving time
                if trip.estimated_driving_time_hours:
                    driving_minutes = int(float(trip.estimated_driving_time_hours) * 60)
                    
                    # Driving to pickup
                    activities.append({
                        'type': 'driving',
                        'start_time': current_time,
                        'duration_minutes': driving_minutes // 2,  # Assume half to pickup
                        'location': trip.pickup_location,
                        'description': 'Driving to pickup location',
                        'miles_driven': trip.total_distance_miles / 2 if trip.total_distance_miles else Decimal('100')
                    })
                    current_time += timedelta(minutes=driving_minutes // 2)
                    
                    # Pickup stop (1 hour)
                    activities.append({
                        'type': 'on_duty_not_driving',
                        'start_time': current_time,
                        'duration_minutes': 60,
                        'location': trip.pickup_location,
                        'description': 'Pickup and loading',
                        'miles_driven': Decimal('0')
                    })
                    current_time += timedelta(hours=1)
                    
                    # Driving to delivery
                    activities.append({
                        'type': 'driving',
                        'start_time': current_time,
                        'duration_minutes': driving_minutes // 2,  # Second half to delivery
                        'location': trip.dropoff_location,
                        'description': 'Driving to delivery location',
                        'miles_driven': trip.total_distance_miles / 2 if trip.total_distance_miles else Decimal('100')
                    })
                    current_time += timedelta(minutes=driving_minutes // 2)
                    timeline['total_driving_hours'] = float(trip.estimated_driving_time_hours)

            # 3. Final delivery/unloading (1 hour)
            activities.append({
                'type': 'on_duty_not_driving',
                'start_time': current_time,
                'duration_minutes': 60,
                'location': trip.dropoff_location,
                'description': 'Delivery and unloading',
                'miles_driven': Decimal('0')
            })
            current_time += timedelta(hours=1)

            # 4. Add required rest breaks
            activities = self._insert_required_rest_breaks(activities, trip)

            # Update timeline
            timeline['activities'] = activities
            timeline['trip_end_time'] = current_time
            timeline['total_trip_hours'] = (current_time - timeline['trip_start_time']).total_seconds() / 3600
            timeline['requires_rest_break'] = timeline['total_driving_hours'] > 8

            return timeline

        except Exception as e:
            self.logger.error(f"Failed to calculate trip timeline: {str(e)}")
            raise

    def _insert_required_rest_breaks(self, activities: List[Dict], trip) -> List[Dict]:
        """Insert required 30-minute breaks and overnight rests."""
        updated_activities = []
        continuous_driving_minutes = 0
        
        for activity in activities:
            if activity['type'] == 'driving':
                continuous_driving_minutes += activity['duration_minutes']
                
                # Add the driving activity first
                updated_activities.append(activity)
                
                # Check if we need a 30-minute break after 8 hours (480 minutes)
                if continuous_driving_minutes >= 480:
                    # Add 30-minute break
                    break_start_time = activity['start_time'] + timedelta(minutes=activity['duration_minutes'])
                    updated_activities.append({
                        'type': 'off_duty',
                        'start_time': break_start_time,
                        'duration_minutes': 30,
                        'location': activity['location'],
                        'description': '30-minute rest break (HOS compliance)',
                        'miles_driven': Decimal('0')
                    })
                    continuous_driving_minutes = 0
                    
                    # Update subsequent activity times
                    for remaining_activity in activities[activities.index(activity) + 1:]:
                        remaining_activity['start_time'] += timedelta(minutes=30)
            else:
                updated_activities.append(activity)
                # Non-driving activities of 30+ minutes reset the continuous driving counter
                if activity['duration_minutes'] >= 30:
                    continuous_driving_minutes = 0

        return updated_activities

    def _determine_daily_log_dates(self, timeline: Dict) -> List[datetime.date]:
        """Determine which dates need daily logs based on trip timeline."""
        start_date = timeline['trip_start_time'].date()
        end_date = timeline['trip_end_time'].date()
        
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        return dates

    def _create_daily_log_for_date(self, trip, log_date: datetime.date, timeline: Dict) -> DailyLog:
        """Create a daily log for a specific date."""
        try:
            self.logger.debug(f"Creating daily log for {log_date}")

            # Create the daily log instance
            daily_log = DailyLog.objects.create(
                trip=trip,
                log_date=log_date,
                driver_name=trip.driver_name,
                carrier_name="Trucking Company",  # Could be configurable
                carrier_main_office_address="Main Office, State",  # Could be configurable
                vehicle_number="TRUCK001",  # Could be from trip or driver profile
                period_start_time=time(0, 0),  # Midnight start
                shipping_document_numbers=f"Trip {trip.id.hex[:8]}",
            )

            # Create duty status records for this date
            self._create_duty_status_records_for_date(daily_log, log_date, timeline)

            # Calculate totals from duty status records
            daily_log.calculate_totals()

            self.logger.info(f"Created daily log {daily_log.id} for {log_date}")
            return daily_log

        except Exception as e:
            self.logger.error(f"Failed to create daily log for {log_date}: {str(e)}")
            raise

    def _create_duty_status_records_for_date(self, daily_log: DailyLog, log_date: datetime.date, timeline: Dict):
        """Create duty status records for a specific date."""
        try:
            # Get activities for this specific date
            date_start = datetime.combine(log_date, time(0, 0))
            date_start = timezone.make_aware(date_start) if date_start.tzinfo is None else date_start
            date_end = date_start + timedelta(days=1)

            # Filter activities that occur on this date
            date_activities = []
            for activity in timeline['activities']:
                activity_start = activity['start_time']
                activity_end = activity_start + timedelta(minutes=activity['duration_minutes'])
                
                # Check if activity overlaps with this date
                if activity_start < date_end and activity_end > date_start:
                    # Calculate the portion that falls within this date
                    clipped_start = max(activity_start, date_start)
                    clipped_end = min(activity_end, date_end)
                    clipped_duration = int((clipped_end - clipped_start).total_seconds() / 60)
                    
                    if clipped_duration > 0:
                        date_activities.append({
                            'type': activity['type'],
                            'start_time': clipped_start,
                            'duration_minutes': clipped_duration,
                            'location': activity['location'],
                            'description': activity['description'],
                            'miles_driven': activity['miles_driven'] if clipped_duration == activity['duration_minutes'] else Decimal('0')
                        })

            # Fill gaps with off_duty time to ensure 24 hours
            date_activities = self._fill_daily_log_gaps(date_activities, date_start, date_end)

            # Create duty status records
            sequence_order = 0
            total_miles = Decimal('0')
            
            for activity in date_activities:
                # Extract city and state from location if possible
                location_city, location_state = self._parse_location(activity['location'])
                
                # Set end_time properly
                end_time = activity['start_time'] + timedelta(minutes=activity['duration_minutes'])
                
                record = DutyStatusRecord.objects.create(
                    daily_log=daily_log,
                    duty_status=activity['type'],
                    start_time=activity['start_time'],
                    end_time=end_time,
                    duration_minutes=activity['duration_minutes'],
                    location_city=location_city,
                    location_state=location_state,
                    location_description=activity['location'],
                    remarks=activity['description'],
                    miles_driven_this_period=activity['miles_driven'],
                    sequence_order=sequence_order,
                    record_type=DutyStatusRecord.RecordType.AUTOMATIC
                )
                
                total_miles += activity['miles_driven']
                sequence_order += 1

            # Update daily log with total miles
            daily_log.total_miles_driving_today = total_miles
            daily_log.save()

        except Exception as e:
            self.logger.error(f"Failed to create duty status records for {log_date}: {str(e)}")
            raise

    def _fill_daily_log_gaps(self, activities: List[Dict], date_start: datetime, date_end: datetime) -> List[Dict]:
        """Fill gaps in daily log to ensure 24-hour coverage."""
        if not activities:
            # Entire day is off duty
            return [{
                'type': 'off_duty',
                'start_time': date_start,
                'duration_minutes': 1440,  # 24 hours
                'location': 'Rest location',
                'description': 'Off duty',
                'miles_driven': Decimal('0')
            }]

        # Sort activities by start time
        sorted_activities = sorted(activities, key=lambda x: x['start_time'])
        filled_activities = []

        # Fill gap at beginning of day if needed
        if sorted_activities[0]['start_time'] > date_start:
            gap_minutes = int((sorted_activities[0]['start_time'] - date_start).total_seconds() / 60)
            filled_activities.append({
                'type': 'off_duty',
                'start_time': date_start,
                'duration_minutes': gap_minutes,
                'location': 'Rest location',
                'description': 'Off duty',
                'miles_driven': Decimal('0')
            })

        # Add all activities and fill gaps between them
        for i, activity in enumerate(sorted_activities):
            filled_activities.append(activity)

            # Fill gap to next activity if it exists
            if i < len(sorted_activities) - 1:
                current_end = activity['start_time'] + timedelta(minutes=activity['duration_minutes'])
                next_start = sorted_activities[i + 1]['start_time']
                
                if next_start > current_end:
                    gap_minutes = int((next_start - current_end).total_seconds() / 60)
                    filled_activities.append({
                        'type': 'off_duty',
                        'start_time': current_end,
                        'duration_minutes': gap_minutes,
                        'location': activity['location'],
                        'description': 'Off duty',
                        'miles_driven': Decimal('0')
                    })

        # Fill gap at end of day if needed
        last_activity = sorted_activities[-1]
        last_end = last_activity['start_time'] + timedelta(minutes=last_activity['duration_minutes'])
        if last_end < date_end:
            gap_minutes = int((date_end - last_end).total_seconds() / 60)
            filled_activities.append({
                'type': 'off_duty',
                'start_time': last_end,
                'duration_minutes': gap_minutes,
                'location': last_activity['location'],
                'description': 'Off duty',
                'miles_driven': Decimal('0')
            })

        return filled_activities

    def _parse_location(self, location_string: str) -> tuple[str, str]:
        """Parse location string to extract city and state."""
        if not location_string:
            return "", ""

        # Try to extract city, state from common patterns
        if "," in location_string:
            parts = location_string.split(",")
            if len(parts) >= 2:
                city = parts[0].strip()
                state = parts[1].strip()
                # Extract state abbreviation if it looks like one
                state_parts = state.split()
                if state_parts and len(state_parts[-1]) == 2:
                    return city, state_parts[-1].upper()
                return city, state[:50]  # Limit state field length

        return location_string[:100], ""  # Return as city if can't parse

    def generate_daily_log_from_timeline(self, trip, start_time: datetime, activities: List[Dict]) -> DailyLog:
        """
        Generate a daily log from a specific timeline.

        Alternative method for more precise control over daily log generation.

        Args:
            trip: Trip model instance
            start_time: When the daily log period starts
            activities: List of activity dictionaries with timing and details

        Returns:
            Generated DailyLog instance
        """
        try:
            with transaction.atomic():
                log_date = start_time.date()
                self.logger.info(f"Generating daily log from custom timeline for {log_date}")

                # Create daily log
                daily_log = DailyLog.objects.create(
                    trip=trip,
                    log_date=log_date,
                    driver_name=trip.driver_name,
                    carrier_name="Trucking Company",
                    carrier_main_office_address="Main Office, State",
                    vehicle_number="TRUCK001",
                    period_start_time=start_time.time(),
                )

                # Create duty status records from activities
                sequence_order = 0
                total_miles = Decimal('0')

                for activity in activities:
                    location_city, location_state = self._parse_location(activity.get('location', ''))
                    
                    record = DutyStatusRecord.objects.create(
                        daily_log=daily_log,
                        duty_status=activity['duty_status'],
                        start_time=activity['start_time'],
                        end_time=activity.get('end_time'),
                        duration_minutes=activity['duration_minutes'],
                        location_city=location_city,
                        location_state=location_state,
                        location_description=activity.get('location', ''),
                        remarks=activity.get('remarks', ''),
                        miles_driven_this_period=activity.get('miles_driven', Decimal('0')),
                        sequence_order=sequence_order,
                        record_type=DutyStatusRecord.RecordType.MANUAL
                    )
                    
                    total_miles += record.miles_driven_this_period
                    sequence_order += 1

                # Update totals
                daily_log.total_miles_driving_today = total_miles
                daily_log.calculate_totals()

                self.logger.info(f"Generated daily log {daily_log.id} from custom timeline")
                return daily_log

        except Exception as e:
            self.logger.error(f"Failed to generate daily log from timeline: {str(e)}")
            raise DailyLogGenerationError(f"Failed to generate daily log: {str(e)}")

    def validate_daily_log_compliance(self, daily_log: DailyLog) -> Dict:
        """Validate a daily log against HOS regulations."""
        try:
            violations = daily_log.validate_compliance()
            
            return {
                'daily_log_id': str(daily_log.id),
                'log_date': daily_log.log_date.isoformat(),
                'is_compliant': len(violations) == 0,
                'violations': violations,
                'totals': daily_log.get_duty_status_summary(),
                'certification': daily_log.get_certification_status()
            }

        except Exception as e:
            self.logger.error(f"Failed to validate daily log compliance: {str(e)}")
            raise


    def generate_logs_for_trip(
        self, 
        trip, 
        start_date, 
        end_date, 
        include_log_sheets=True, 
        sheet_format='pdf'
    ) -> Dict:
        """
        Generate ELD logs for a trip within date range (for API compatibility).
        
        Args:
            trip: Trip instance
            start_date: Start date for generation
            end_date: End date for generation  
            include_log_sheets: Whether to generate visual log sheets
            sheet_format: Format for log sheets
            
        Returns:
            Dict containing generation results
        """
        try:
            self.logger.info(f"Generating logs for trip {trip.id} from {start_date} to {end_date}")
            
            # Generate daily logs
            daily_logs = self.generate_trip_daily_logs(trip)
            
            # Filter logs by date range
            filtered_logs = [
                log for log in daily_logs 
                if start_date <= log.log_date <= end_date
            ]
            
            # Generate log sheets if requested
            generated_sheets = []
            if include_log_sheets:
                from .log_sheet_renderer import LogSheetRendererService
                renderer = LogSheetRendererService()
                
                for daily_log in filtered_logs:
                    try:
                        sheet = renderer.generate_log_sheet(daily_log, sheet_format)
                        generated_sheets.append(sheet)
                    except Exception as e:
                        self.logger.warning(f"Failed to generate sheet for log {daily_log.id}: {str(e)}")
            
            return {
                'generated_logs': filtered_logs,
                'generated_sheets': generated_sheets,
                'errors': [],
                'warnings': []
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate logs for trip: {str(e)}")
            return {
                'generated_logs': [],
                'generated_sheets': [],
                'errors': [str(e)],
                'warnings': []
            }


class DailyLogGenerationError(Exception):
    """Exception raised when daily log generation fails."""
    pass


# Alias for backwards compatibility
ELDLogGeneratorService = DailyLogGeneratorService
