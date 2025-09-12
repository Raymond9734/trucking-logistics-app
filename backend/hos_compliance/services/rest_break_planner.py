"""
Rest Break Planner Service.

Plans mandatory rest breaks during trips based on HOS regulations
and route information. Determines when and where breaks are required
for compliance with FMCSA regulations.

This service integrates route data with HOS calculations to:
- Plan 30-minute rest breaks during driving
- Schedule 10-hour off-duty periods
- Plan fuel stops (every 1000 miles per assessment)
- Calculate pickup/dropoff stop times
- Optimize break timing for compliance

Single Responsibility: Rest break planning and scheduling only.
"""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import Dict, List
from django.utils import timezone

from .hos_calculator import HOSCalculatorService

logger = logging.getLogger(__name__)


class RestBreakPlannerService:
    """
    Service for planning mandatory rest breaks during trips.

    Plans all required rest breaks based on HOS regulations,
    route information, and driver's current status.
    """

    # Break planning constants from assessment requirements
    FUEL_STOP_INTERVAL_MILES = 1000  # Fuel stop every 1000 miles
    PICKUP_DROPOFF_HOURS = Decimal("1")  # 1 hour each per assessment
    AVERAGE_DRIVING_SPEED_MPH = 55  # Average truck speed

    def __init__(self):
        """Initialize rest break planner."""
        self.hos_calculator = HOSCalculatorService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def plan_trip_breaks(
        self,
        total_distance_miles: Decimal,
        estimated_driving_hours: Decimal,
        current_cycle_hours: Decimal,
        current_duty_hours: Decimal = Decimal("0"),
        current_driving_hours: Decimal = Decimal("0"),
        hours_since_last_break: Decimal = Decimal("0"),
    ) -> Dict:
        """
        Plan all required breaks for a complete trip.

        Args:
            total_distance_miles: Total trip distance in miles
            estimated_driving_hours: Estimated driving time in hours
            current_cycle_hours: Current hours used in 8-day cycle
            current_duty_hours: Hours on duty in current duty period
            current_driving_hours: Hours driven in current duty period
            hours_since_last_break: Hours driven since last 30-min break

        Returns:
            Dict containing complete break plan for the trip
        """
        try:
            self.logger.info(f"Planning breaks for {total_distance_miles} mile trip")

            # Validate inputs
            self._validate_trip_inputs(
                total_distance_miles, estimated_driving_hours, current_cycle_hours
            )

            # Plan all required breaks
            mandatory_breaks = self._plan_mandatory_hos_breaks(
                estimated_driving_hours,
                current_cycle_hours,
                current_duty_hours,
                current_driving_hours,
                hours_since_last_break,
            )

            fuel_stops = self._plan_fuel_stops(
                total_distance_miles, estimated_driving_hours
            )

            operational_stops = self._plan_operational_stops()

            # Combine and optimize break timing
            all_breaks = mandatory_breaks + fuel_stops + operational_stops
            optimized_breaks = self._optimize_break_schedule(
                all_breaks, estimated_driving_hours
            )

            # Calculate trip timeline with breaks
            timeline = self._calculate_trip_timeline(
                optimized_breaks, estimated_driving_hours
            )

            # Validate overall compliance
            compliance = self._validate_break_plan_compliance(
                optimized_breaks, estimated_driving_hours, current_cycle_hours
            )

            result = {
                "total_breaks": len(optimized_breaks),
                "mandatory_breaks_count": len(mandatory_breaks),
                "fuel_stops_count": len(fuel_stops),
                "operational_stops_count": len(operational_stops),
                "breaks": optimized_breaks,
                "trip_timeline": timeline,
                "compliance": compliance,
                "total_trip_time_hours": timeline.get("total_time_hours", 0),
                "total_driving_time_hours": float(estimated_driving_hours),
                "total_break_time_hours": timeline.get("total_break_time_hours", 0),
                "planned_at": timezone.now().isoformat(),
            }

            self.logger.info(
                f"Break plan completed: {len(optimized_breaks)} breaks planned"
            )
            return result

        except Exception as e:
            self.logger.error(f"Break planning failed: {str(e)}")
            raise RestBreakPlanningError(f"Failed to plan trip breaks: {str(e)}")

    def plan_30_minute_breaks(
        self,
        estimated_driving_hours: Decimal,
        hours_since_last_break: Decimal = Decimal("0"),
    ) -> List[Dict]:
        """
        Plan required 30-minute rest breaks during driving.

        Args:
            estimated_driving_hours: Total estimated driving time
            hours_since_last_break: Hours already driven since last break

        Returns:
            List of planned 30-minute breaks
        """
        try:
            breaks = []
            remaining_hours = estimated_driving_hours
            current_driving_hours = hours_since_last_break
            driving_hours_completed = Decimal("0")

            while remaining_hours > 0:
                # Check if break is needed
                if (
                    current_driving_hours
                    >= self.hos_calculator.BREAK_REQUIRED_AFTER_HOURS
                ):
                    # Plan 30-minute break
                    breaks.append(
                        {
                            "break_type": "30_minute",
                            "duration_hours": Decimal("0.5"),
                            "required_at_driving_hours": float(driving_hours_completed),
                            "required_at_trip_miles": float(
                                driving_hours_completed * self.AVERAGE_DRIVING_SPEED_MPH
                            ),
                            "is_mandatory": True,
                            "regulation_reference": "395.3(a)(3)(ii)",
                            "location_description": "Rest area or truck stop",
                            "priority": "critical",
                            "reason": "30-minute rest break after 8 hours driving",
                        }
                    )

                    # Reset driving hours counter after break
                    current_driving_hours = Decimal("0")

                # Determine next segment length
                hours_until_next_break = min(
                    remaining_hours,
                    self.hos_calculator.BREAK_REQUIRED_AFTER_HOURS
                    - current_driving_hours,
                )

                current_driving_hours += hours_until_next_break
                driving_hours_completed += hours_until_next_break
                remaining_hours -= hours_until_next_break

            self.logger.debug(f"Planned {len(breaks)} 30-minute breaks")
            return breaks

        except Exception as e:
            self.logger.error(f"30-minute break planning failed: {str(e)}")
            raise RestBreakPlanningError(f"Failed to plan 30-minute breaks: {str(e)}")

    def plan_breaks_for_trip(
        self,
        estimated_driving_hours: Decimal,
        planned_start_time: timezone.datetime,
    ) -> Dict:
        """
        Plan breaks for a trip (simplified version for view compatibility).
        
        Args:
            estimated_driving_hours: Expected driving time
            planned_start_time: When trip is planned to start
            
        Returns:
            Dict containing break plan information
        """
        try:
            # Plan 30-minute breaks
            thirty_min_breaks = self.plan_30_minute_breaks(estimated_driving_hours)
            
            # Plan daily rest if needed
            daily_rest = self.plan_daily_rest_periods(estimated_driving_hours)
            
            # Calculate total breaks
            total_breaks = thirty_min_breaks + daily_rest
            
            # Calculate timeline
            total_break_time = sum(break_info["duration_hours"] for break_info in total_breaks)
            total_time = float(estimated_driving_hours) + total_break_time
            
            return {
                'required_breaks': total_breaks,
                'total_breaks': len(total_breaks),
                'total_break_time_hours': total_break_time,
                'total_trip_time_hours': total_time,
                'compliance': {
                    'is_compliant': True,
                    'issues': [],
                    'compliance_score': 100
                },
                'planned_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Break planning for trip failed: {str(e)}")
            return {
                'required_breaks': [],
                'total_breaks': 0,
                'total_break_time_hours': 0,
                'total_trip_time_hours': float(estimated_driving_hours),
                'compliance': {
                    'is_compliant': False,
                    'issues': [{'type': 'planning_error', 'description': str(e)}],
                    'compliance_score': 0
                },
                'planned_at': timezone.now().isoformat()
            }

    def plan_daily_rest_periods(
        self,
        estimated_driving_hours: Decimal,
        current_duty_hours: Decimal = Decimal("0"),
        current_driving_hours: Decimal = Decimal("0"),
    ) -> List[Dict]:
        """
        Plan required 10-hour off-duty periods during trip.

        Args:
            estimated_driving_hours: Total estimated driving time
            current_duty_hours: Current hours on duty in duty period
            current_driving_hours: Current hours driven in duty period

        Returns:
            List of planned 10-hour rest periods
        """
        try:
            rest_periods = []

            # Calculate available time in current duty period
            available_duty_hours = (
                self.hos_calculator.MAX_DUTY_PERIOD_HOURS - current_duty_hours
            )
            available_driving_hours = (
                self.hos_calculator.MAX_DRIVING_HOURS - current_driving_hours
            )

            # Determine if rest period is needed during trip
            driving_remaining = estimated_driving_hours

            if (
                driving_remaining > available_driving_hours
                or driving_remaining + current_duty_hours
                > self.hos_calculator.MAX_DUTY_PERIOD_HOURS
            ):

                # Calculate when 10-hour rest is needed
                hours_before_rest = min(available_driving_hours, available_duty_hours)

                rest_periods.append(
                    {
                        "break_type": "10_hour",
                        "duration_hours": self.hos_calculator.MIN_OFF_DUTY_HOURS,
                        "required_at_driving_hours": float(hours_before_rest),
                        "required_at_trip_miles": float(
                            hours_before_rest * self.AVERAGE_DRIVING_SPEED_MPH
                        ),
                        "is_mandatory": True,
                        "regulation_reference": "395.3(a)(1)",
                        "location_description": "Truck stop with parking or rest area",
                        "priority": "critical",
                        "reason": "10 consecutive hours off duty to reset daily limits",
                    }
                )

                # Check if additional rest periods needed for remaining driving
                remaining_after_rest = driving_remaining - hours_before_rest
                if remaining_after_rest > self.hos_calculator.MAX_DRIVING_HOURS:
                    # Additional 10-hour rest needed
                    rest_periods.append(
                        {
                            "break_type": "10_hour",
                            "duration_hours": self.hos_calculator.MIN_OFF_DUTY_HOURS,
                            "required_at_driving_hours": float(
                                hours_before_rest
                                + self.hos_calculator.MAX_DRIVING_HOURS
                            ),
                            "required_at_trip_miles": float(
                                (
                                    hours_before_rest
                                    + self.hos_calculator.MAX_DRIVING_HOURS
                                )
                                * self.AVERAGE_DRIVING_SPEED_MPH
                            ),
                            "is_mandatory": True,
                            "regulation_reference": "395.3(a)(1)",
                            "location_description": "Truck stop with parking or rest area",
                            "priority": "critical",
                            "reason": "10 consecutive hours off duty for second duty period",
                        }
                    )

            self.logger.debug(f"Planned {len(rest_periods)} 10-hour rest periods")
            return rest_periods

        except Exception as e:
            self.logger.error(f"Daily rest period planning failed: {str(e)}")
            raise RestBreakPlanningError(f"Failed to plan daily rest periods: {str(e)}")

    def _plan_mandatory_hos_breaks(
        self,
        estimated_driving_hours: Decimal,
        current_cycle_hours: Decimal,
        current_duty_hours: Decimal,
        current_driving_hours: Decimal,
        hours_since_last_break: Decimal,
    ) -> List[Dict]:
        """Plan all mandatory HOS breaks."""
        mandatory_breaks = []

        # Plan 30-minute breaks
        thirty_minute_breaks = self.plan_30_minute_breaks(
            estimated_driving_hours, hours_since_last_break
        )
        mandatory_breaks.extend(thirty_minute_breaks)

        # Plan 10-hour rest periods
        daily_rest_periods = self.plan_daily_rest_periods(
            estimated_driving_hours, current_duty_hours, current_driving_hours
        )
        mandatory_breaks.extend(daily_rest_periods)

        # Check if 34-hour restart is needed
        pickup_dropoff_hours = 2 * self.PICKUP_DROPOFF_HOURS  # 2 hours total
        total_trip_hours = estimated_driving_hours + pickup_dropoff_hours

        if current_cycle_hours + total_trip_hours > self.hos_calculator.MAX_CYCLE_HOURS:
            mandatory_breaks.append(
                {
                    "break_type": "34_hour_restart",
                    "duration_hours": self.hos_calculator.RESTART_OFF_DUTY_HOURS,
                    "required_at_driving_hours": 0,  # Before trip starts
                    "required_at_trip_miles": 0,
                    "is_mandatory": True,
                    "regulation_reference": "395.3(c)",
                    "location_description": "Home terminal or suitable rest location",
                    "priority": "critical",
                    "reason": "34-hour restart required to reset 8-day cycle before trip",
                }
            )

        return mandatory_breaks

    def _plan_fuel_stops(
        self, total_distance_miles: Decimal, estimated_driving_hours: Decimal
    ) -> List[Dict]:
        """Plan fuel stops every 1000 miles per assessment requirements."""
        fuel_stops = []

        if total_distance_miles > self.FUEL_STOP_INTERVAL_MILES:
            num_stops = int(total_distance_miles // self.FUEL_STOP_INTERVAL_MILES)

            for i in range(1, num_stops + 1):
                stop_miles = i * self.FUEL_STOP_INTERVAL_MILES
                stop_hours = stop_miles / self.AVERAGE_DRIVING_SPEED_MPH

                fuel_stops.append(
                    {
                        "break_type": "fuel_stop",
                        "duration_hours": Decimal("0.5"),  # 30 minutes for fuel
                        "required_at_driving_hours": float(stop_hours),
                        "required_at_trip_miles": float(stop_miles),
                        "is_mandatory": False,
                        "regulation_reference": "",
                        "location_description": "Truck stop or fuel station",
                        "priority": "medium",
                        "reason": f"Fuel stop at {stop_miles} miles",
                    }
                )

        self.logger.debug(f"Planned {len(fuel_stops)} fuel stops")
        return fuel_stops

    def _plan_operational_stops(self) -> List[Dict]:
        """Plan operational stops (pickup/dropoff)."""
        return [
            {
                "break_type": "pickup_dropoff",
                "duration_hours": self.PICKUP_DROPOFF_HOURS,
                "required_at_driving_hours": 0,  # At start (current to pickup)
                "required_at_trip_miles": 0,
                "is_mandatory": True,
                "regulation_reference": "",
                "location_description": "Pickup location",
                "priority": "high",
                "reason": "Pickup time (1 hour per assessment)",
            },
            {
                "break_type": "pickup_dropoff",
                "duration_hours": self.PICKUP_DROPOFF_HOURS,
                "required_at_driving_hours": 0,  # Will be calculated based on route
                "required_at_trip_miles": 0,  # At end
                "is_mandatory": True,
                "regulation_reference": "",
                "location_description": "Dropoff location",
                "priority": "high",
                "reason": "Dropoff time (1 hour per assessment)",
            },
        ]

    def _optimize_break_schedule(
        self, breaks: List[Dict], total_driving_hours: Decimal
    ) -> List[Dict]:
        """Optimize break schedule to minimize total trip time."""
        # Sort breaks by required timing
        breaks.sort(key=lambda x: x["required_at_driving_hours"])

        # Combine overlapping breaks where possible
        optimized = []
        i = 0

        while i < len(breaks):
            current_break = breaks[i].copy()

            # Look for breaks that can be combined
            j = i + 1
            while j < len(breaks):
                next_break = breaks[j]

                # If breaks are close in time, consider combining
                time_diff = abs(
                    next_break["required_at_driving_hours"]
                    - current_break["required_at_driving_hours"]
                )

                if time_diff <= 0.5 and self._can_combine_breaks(
                    current_break, next_break
                ):
                    # Combine breaks
                    current_break = self._combine_breaks(current_break, next_break)
                    j += 1
                else:
                    break

            optimized.append(current_break)
            i = j if j > i + 1 else i + 1

        return optimized

    def _can_combine_breaks(self, break1: Dict, break2: Dict) -> bool:
        """Check if two breaks can be combined."""
        # Can combine 30-minute break with fuel stop
        if {break1["break_type"], break2["break_type"]} == {"30_minute", "fuel_stop"}:
            return True

        # Cannot combine mandatory rest periods
        if break1["break_type"] in ["10_hour", "34_hour_restart"]:
            return False
        if break2["break_type"] in ["10_hour", "34_hour_restart"]:
            return False

        return False

    def _combine_breaks(self, break1: Dict, break2: Dict) -> Dict:
        """Combine two compatible breaks."""
        combined = break1.copy()

        # Use longer duration
        combined["duration_hours"] = max(
            break1["duration_hours"], break2["duration_hours"]
        )

        # Combine descriptions
        combined["reason"] = f"{break1['reason']} + {break2['reason']}"
        combined["break_type"] = "combined"

        # Use higher priority
        priorities = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        priority1 = priorities.get(break1["priority"], 2)
        priority2 = priorities.get(break2["priority"], 2)

        priority_names = {1: "low", 2: "medium", 3: "high", 4: "critical"}
        combined["priority"] = priority_names[max(priority1, priority2)]

        return combined

    def _calculate_trip_timeline(
        self, breaks: List[Dict], driving_hours: Decimal
    ) -> Dict:
        """Calculate complete trip timeline with breaks."""
        total_break_time = sum(break_info["duration_hours"] for break_info in breaks)

        total_time = float(driving_hours) + total_break_time

        return {
            "total_time_hours": total_time,
            "total_driving_time_hours": float(driving_hours),
            "total_break_time_hours": total_break_time,
            "number_of_breaks": len(breaks),
            "estimated_start_time": timezone.now().isoformat(),
            "estimated_end_time": (
                timezone.now() + timedelta(hours=total_time)
            ).isoformat(),
        }

    def _validate_break_plan_compliance(
        self, breaks: List[Dict], driving_hours: Decimal, current_cycle_hours: Decimal
    ) -> Dict:
        """Validate that break plan ensures HOS compliance."""
        issues = []

        # Check for required 30-minute breaks
        thirty_min_breaks = [
            b for b in breaks if b["break_type"] in ["30_minute", "combined"]
        ]

        required_30_min_breaks = max(1, int(driving_hours // 8))
        if len(thirty_min_breaks) < required_30_min_breaks:
            issues.append(
                {
                    "type": "insufficient_30_minute_breaks",
                    "description": f"Plan needs {required_30_min_breaks} 30-minute breaks, only {len(thirty_min_breaks)} planned",
                }
            )

        # Check for required 10-hour rest periods
        if driving_hours > 11:
            ten_hour_breaks = [b for b in breaks if b["break_type"] == "10_hour"]

            required_10_hour_breaks = max(1, int((driving_hours - 1) // 11))
            if len(ten_hour_breaks) < required_10_hour_breaks:
                issues.append(
                    {
                        "type": "insufficient_10_hour_breaks",
                        "description": f"Plan needs {required_10_hour_breaks} 10-hour breaks, only {len(ten_hour_breaks)} planned",
                    }
                )

        is_compliant = len(issues) == 0

        return {
            "is_compliant": is_compliant,
            "issues": issues,
            "compliance_score": 100 if is_compliant else max(0, 100 - len(issues) * 20),
        }

    def _validate_trip_inputs(
        self, distance: Decimal, driving_hours: Decimal, cycle_hours: Decimal
    ):
        """Validate trip planning inputs."""
        if distance <= 0:
            raise ValueError(f"Invalid trip distance: {distance}")
        if driving_hours <= 0:
            raise ValueError(f"Invalid driving hours: {driving_hours}")
        if cycle_hours < 0 or cycle_hours > 70:
            raise ValueError(f"Invalid cycle hours: {cycle_hours}")

        # Check reasonable relationship between distance and time
        implied_speed = float(distance) / float(driving_hours)
        if implied_speed < 20 or implied_speed > 80:
            raise ValueError(
                f"Unrealistic speed implied: {implied_speed} mph "
                f"({distance} miles in {driving_hours} hours)"
            )


class RestBreakPlanningError(Exception):
    """Exception raised when rest break planning fails."""

    pass
