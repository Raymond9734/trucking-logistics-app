"""
HOS Calculator Service.

Provides core Hours of Service calculations and rule validation
based on FMCSA regulations for property-carrying commercial vehicles.

This service implements the fundamental HOS business logic including:
- 70 hours in 8 days cycle calculation
- 14-hour driving window validation
- 11-hour driving limit calculation
- 30-minute break requirements
- 10-hour off-duty rest validation

Single Responsibility: HOS calculations and rule validation only.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)


class HOSCalculatorService:
    """
    Service for calculating Hours of Service compliance.

    Handles all core HOS calculations based on FMCSA regulations
    for property-carrying commercial vehicles.
    """

    # HOS regulation constants
    MAX_CYCLE_HOURS = Decimal("70")  # 70 hours in 8 days
    MAX_DUTY_PERIOD_HOURS = Decimal("14")  # 14-hour driving window
    MAX_DRIVING_HOURS = Decimal("11")  # 11 hours driving in duty period
    REQUIRED_BREAK_MINUTES = 30  # 30-minute break after 8 hours driving
    BREAK_REQUIRED_AFTER_HOURS = Decimal("8")  # Break required after 8 hours driving
    MIN_OFF_DUTY_HOURS = Decimal("10")  # 10 hours off duty to reset
    RESTART_OFF_DUTY_HOURS = Decimal("34")  # 34 hours off duty for restart

    def __init__(self):
        """Initialize HOS calculator with regulatory constants."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def calculate_available_hours(
        self,
        current_cycle_hours: Decimal,
        current_duty_period_hours: Decimal = Decimal("0"),
        current_driving_hours: Decimal = Decimal("0"),
        hours_since_last_break: Decimal = Decimal("0"),
    ) -> Dict:
        """
        Calculate available hours under all HOS limits.

        Args:
            current_cycle_hours: Hours used in current 8-day cycle
            current_duty_period_hours: Hours on duty in current 14-hour window
            current_driving_hours: Hours driven in current duty period
            hours_since_last_break: Hours driven since last 30-min break

        Returns:
            Dict containing all calculated available hours and compliance status
        """
        try:
            # Validate input parameters
            self._validate_hours_input(
                current_cycle_hours,
                current_duty_period_hours,
                current_driving_hours,
                hours_since_last_break,
            )

            # Calculate available hours for each limit
            available_cycle = max(
                Decimal("0"), self.MAX_CYCLE_HOURS - current_cycle_hours
            )
            available_duty_period = max(
                Decimal("0"), self.MAX_DUTY_PERIOD_HOURS - current_duty_period_hours
            )
            available_driving = max(
                Decimal("0"), self.MAX_DRIVING_HOURS - current_driving_hours
            )

            # Calculate hours until 30-minute break required
            hours_until_break = max(
                Decimal("0"), self.BREAK_REQUIRED_AFTER_HOURS - hours_since_last_break
            )

            # Determine if driver can drive now
            can_drive, violation_reason = self._check_can_drive(
                available_cycle,
                available_duty_period,
                available_driving,
                hours_until_break,
            )

            # Calculate maximum continuous driving time
            max_continuous_driving = self._calculate_max_continuous_driving(
                available_cycle,
                available_duty_period,
                available_driving,
                hours_until_break,
            )

            result = {
                "can_drive": can_drive,
                "violation_reason": violation_reason,
                "available_hours": {
                    "cycle_hours": float(available_cycle),
                    "duty_period_hours": float(available_duty_period),
                    "driving_hours": float(available_driving),
                    "hours_until_break": float(hours_until_break),
                },
                "limits": {
                    "max_cycle_hours": float(self.MAX_CYCLE_HOURS),
                    "max_duty_period_hours": float(self.MAX_DUTY_PERIOD_HOURS),
                    "max_driving_hours": float(self.MAX_DRIVING_HOURS),
                    "break_required_after_hours": float(
                        self.BREAK_REQUIRED_AFTER_HOURS
                    ),
                },
                "current_usage": {
                    "cycle_hours": float(current_cycle_hours),
                    "duty_period_hours": float(current_duty_period_hours),
                    "driving_hours": float(current_driving_hours),
                    "hours_since_last_break": float(hours_since_last_break),
                },
                "max_continuous_driving_hours": float(max_continuous_driving),
                "calculated_at": timezone.now().isoformat(),
            }

            self.logger.debug(f"HOS calculation completed: can_drive={can_drive}")
            return result

        except Exception as e:
            self.logger.error(f"HOS calculation failed: {str(e)}")
            raise HOSCalculationError(f"Failed to calculate available hours: {str(e)}")

    def calculate_required_rest(
        self,
        current_cycle_hours: Decimal,
        current_duty_period_hours: Decimal = Decimal("0"),
        current_driving_hours: Decimal = Decimal("0"),
        needs_30_minute_break: bool = False,
    ) -> Dict:
        """
        Calculate required rest time to comply with HOS regulations.

        Args:
            current_cycle_hours: Hours used in current 8-day cycle
            current_duty_period_hours: Hours on duty in current 14-hour window
            current_driving_hours: Hours driven in current duty period
            needs_30_minute_break: Whether 30-minute break is needed

        Returns:
            Dict containing required rest information
        """
        try:
            rest_options = []

            # Check if 30-minute break is needed
            if needs_30_minute_break:
                rest_options.append(
                    {
                        "type": "30_minute_break",
                        "duration_hours": Decimal("0.5"),
                        "description": "30-minute rest break required after 8 hours driving",
                        "regulation": "395.3(a)(3)(ii)",
                        "restores": ["driving_eligibility"],
                    }
                )

            # Check if 10-hour off-duty period is needed
            if (
                current_driving_hours >= self.MAX_DRIVING_HOURS
                or current_duty_period_hours >= self.MAX_DUTY_PERIOD_HOURS
            ):

                rest_options.append(
                    {
                        "type": "10_hour_off_duty",
                        "duration_hours": self.MIN_OFF_DUTY_HOURS,
                        "description": "10 consecutive hours off duty to reset daily limits",
                        "regulation": "395.3(a)(1)",
                        "restores": ["duty_period", "driving_hours"],
                    }
                )

            # Check if 34-hour restart would be beneficial
            if current_cycle_hours >= 60:  # Near cycle limit
                rest_options.append(
                    {
                        "type": "34_hour_restart",
                        "duration_hours": self.RESTART_OFF_DUTY_HOURS,
                        "description": "34 consecutive hours off duty to restart 8-day cycle",
                        "regulation": "395.3(c)",
                        "restores": ["cycle_hours", "duty_period", "driving_hours"],
                    }
                )

            # Determine minimum required rest
            min_required_rest = Decimal("0")
            required_rest_type = None

            if needs_30_minute_break:
                min_required_rest = Decimal("0.5")
                required_rest_type = "30_minute_break"
            elif (
                current_driving_hours >= self.MAX_DRIVING_HOURS
                or current_duty_period_hours >= self.MAX_DUTY_PERIOD_HOURS
            ):
                min_required_rest = self.MIN_OFF_DUTY_HOURS
                required_rest_type = "10_hour_off_duty"

            return {
                "minimum_required_rest_hours": float(min_required_rest),
                "required_rest_type": required_rest_type,
                "rest_options": [
                    {**option, "duration_hours": float(option["duration_hours"])}
                    for option in rest_options
                ],
                "can_drive_after_minimum_rest": True,
                "calculated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Required rest calculation failed: {str(e)}")
            raise HOSCalculationError(f"Failed to calculate required rest: {str(e)}")

    def calculate_cycle_hours_for_trip(
        self, estimated_driving_hours: Decimal, current_cycle_hours: Decimal
    ) -> Dict:
        """
        Calculate cycle hours impact for a planned trip.

        Args:
            estimated_driving_hours: Expected driving time for trip
            current_cycle_hours: Current hours used in 8-day cycle

        Returns:
            Dict containing cycle analysis for trip
        """
        try:
            # Estimate total on-duty time (driving + pickup/dropoff time)
            pickup_dropoff_hours = Decimal("2")  # 1 hour each per assessment
            estimated_total_hours = estimated_driving_hours + pickup_dropoff_hours

            # Calculate projected cycle hours after trip
            projected_cycle_hours = current_cycle_hours + estimated_total_hours

            # Check if trip exceeds cycle limit
            exceeds_cycle_limit = projected_cycle_hours > self.MAX_CYCLE_HOURS

            # Calculate maximum possible trip hours
            max_possible_hours = self.MAX_CYCLE_HOURS - current_cycle_hours

            return {
                "current_cycle_hours": float(current_cycle_hours),
                "estimated_trip_hours": float(estimated_total_hours),
                "estimated_driving_hours": float(estimated_driving_hours),
                "estimated_pickup_dropoff_hours": float(pickup_dropoff_hours),
                "projected_cycle_hours": float(projected_cycle_hours),
                "cycle_limit": float(self.MAX_CYCLE_HOURS),
                "exceeds_cycle_limit": exceeds_cycle_limit,
                "max_possible_trip_hours": float(max_possible_hours),
                "requires_34_hour_restart": exceeds_cycle_limit,
                "hours_over_limit": float(
                    max(Decimal("0"), projected_cycle_hours - self.MAX_CYCLE_HOURS)
                ),
                "calculated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Cycle hours calculation failed: {str(e)}")
            raise HOSCalculationError(
                f"Failed to calculate cycle hours for trip: {str(e)}"
            )

    def validate_hos_compliance(
        self,
        current_cycle_hours: Decimal,
        current_duty_period_hours: Decimal,
        current_driving_hours: Decimal,
        hours_since_last_break: Decimal,
    ) -> Dict:
        """
        Validate current HOS status against all regulations.

        Args:
            current_cycle_hours: Hours used in current 8-day cycle
            current_duty_period_hours: Hours on duty in current 14-hour window
            current_driving_hours: Hours driven in current duty period
            hours_since_last_break: Hours driven since last 30-min break

        Returns:
            Dict containing comprehensive compliance validation
        """
        try:
            violations = []
            warnings = []

            # Check 70-hour/8-day limit
            if current_cycle_hours > self.MAX_CYCLE_HOURS:
                violations.append(
                    {
                        "type": "cycle_hours_exceeded",
                        "regulation": "395.3(b)",
                        "description": f"Cycle hours ({current_cycle_hours}) exceeds 70-hour limit",
                        "hours_over": float(current_cycle_hours - self.MAX_CYCLE_HOURS),
                    }
                )
            elif (
                current_cycle_hours >= self.MAX_CYCLE_HOURS - 5
            ):  # Within 5 hours of limit
                warnings.append(
                    {
                        "type": "approaching_cycle_limit",
                        "description": f"Approaching 70-hour cycle limit (currently at {current_cycle_hours} hours)",
                        "hours_remaining": float(
                            self.MAX_CYCLE_HOURS - current_cycle_hours
                        ),
                    }
                )

            # Check 14-hour duty period limit
            if current_duty_period_hours > self.MAX_DUTY_PERIOD_HOURS:
                violations.append(
                    {
                        "type": "duty_period_exceeded",
                        "regulation": "395.3(a)(2)",
                        "description": f"Duty period ({current_duty_period_hours}) exceeds 14-hour limit",
                        "hours_over": float(
                            current_duty_period_hours - self.MAX_DUTY_PERIOD_HOURS
                        ),
                    }
                )

            # Check 11-hour driving limit
            if current_driving_hours > self.MAX_DRIVING_HOURS:
                violations.append(
                    {
                        "type": "driving_hours_exceeded",
                        "regulation": "395.3(a)(3)",
                        "description": f"Driving hours ({current_driving_hours}) exceeds 11-hour limit",
                        "hours_over": float(
                            current_driving_hours - self.MAX_DRIVING_HOURS
                        ),
                    }
                )

            # Check 30-minute break requirement
            if hours_since_last_break > self.BREAK_REQUIRED_AFTER_HOURS:
                violations.append(
                    {
                        "type": "break_required",
                        "regulation": "395.3(a)(3)(ii)",
                        "description": f"30-minute break required after 8 hours driving (currently at {hours_since_last_break} hours)",
                        "hours_over": float(
                            hours_since_last_break - self.BREAK_REQUIRED_AFTER_HOURS
                        ),
                    }
                )
            elif (
                hours_since_last_break >= self.BREAK_REQUIRED_AFTER_HOURS - 1
            ):  # Within 1 hour
                warnings.append(
                    {
                        "type": "break_needed_soon",
                        "description": f"30-minute break will be required soon (driven {hours_since_last_break} of 8 hours)",
                        "hours_until_required": float(
                            self.BREAK_REQUIRED_AFTER_HOURS - hours_since_last_break
                        ),
                    }
                )

            is_compliant = len(violations) == 0
            compliance_score = self._calculate_compliance_score(violations, warnings)

            return {
                "is_compliant": is_compliant,
                "compliance_score": compliance_score,
                "violations": violations,
                "warnings": warnings,
                "total_violations": len(violations),
                "total_warnings": len(warnings),
                "can_continue_driving": is_compliant,
                "validated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"HOS compliance validation failed: {str(e)}")
            raise HOSCalculationError(f"Failed to validate HOS compliance: {str(e)}")

    def _validate_hours_input(
        self,
        cycle_hours: Decimal,
        duty_hours: Decimal,
        driving_hours: Decimal,
        break_hours: Decimal,
    ):
        """Validate input hours are reasonable."""
        if cycle_hours < 0 or cycle_hours > 100:
            raise ValueError(f"Invalid cycle hours: {cycle_hours}")
        if duty_hours < 0 or duty_hours > 24:
            raise ValueError(f"Invalid duty period hours: {duty_hours}")
        if driving_hours < 0 or driving_hours > duty_hours:
            raise ValueError(f"Invalid driving hours: {driving_hours}")
        if break_hours < 0 or break_hours > 24:
            raise ValueError(f"Invalid hours since break: {break_hours}")

    def _check_can_drive(
        self,
        available_cycle: Decimal,
        available_duty: Decimal,
        available_driving: Decimal,
        hours_until_break: Decimal,
    ) -> Tuple[bool, str]:
        """Check if driver can currently drive."""
        if available_cycle <= 0:
            return False, "70-hour/8-day limit reached"
        if available_duty <= 0:
            return False, "14-hour duty period limit reached"
        if available_driving <= 0:
            return False, "11-hour driving limit reached"
        if hours_until_break <= 0:
            return False, "30-minute break required after 8 hours driving"

        return True, ""

    def _calculate_max_continuous_driving(
        self,
        available_cycle: Decimal,
        available_duty: Decimal,
        available_driving: Decimal,
        hours_until_break: Decimal,
    ) -> Decimal:
        """Calculate maximum continuous driving time."""
        limits = [available_cycle, available_duty, available_driving]

        if hours_until_break > 0:
            limits.append(hours_until_break)
        else:
            # If break is needed, can't drive continuously
            return Decimal("0")

        return max(Decimal("0"), min(limits))

    def _calculate_compliance_score(
        self, violations: List[Dict], warnings: List[Dict]
    ) -> int:
        """Calculate compliance score (0-100)."""
        score = 100
        score -= len(violations) * 25  # Each violation: -25 points
        score -= len(warnings) * 5  # Each warning: -5 points
        return max(0, min(100, score))


class HOSCalculationError(Exception):
    """Exception raised when HOS calculations fail."""

    pass
