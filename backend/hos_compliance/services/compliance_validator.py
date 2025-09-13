"""
Compliance Validator Service.

Validates trip plans and driver status against HOS regulations.
Provides comprehensive compliance checking for trips, routes,
and driver schedules to ensure FMCSA regulatory compliance.

This service integrates HOS calculations with trip data to:
- Validate trip feasibility under HOS regulations
- Check route compliance with driving limits
- Validate driver eligibility for trips
- Provide compliance recommendations
- Generate compliance reports

Single Responsibility: HOS compliance validation only.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.utils import timezone

from .hos_calculator import HOSCalculatorService
from .rest_break_planner import RestBreakPlannerService

logger = logging.getLogger(__name__)


class ComplianceValidatorService:
    """
    Service for validating HOS compliance for trips and driver status.

    Provides comprehensive compliance validation combining HOS calculations
    with trip planning and break scheduling.
    """

    def __init__(self):
        """Initialize compliance validator with required services."""
        self.hos_calculator = HOSCalculatorService()
        self.break_planner = RestBreakPlannerService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_trip_compliance(self, trip_data: Dict, driver_status: Dict) -> Dict:
        """
        Validate complete trip compliance with HOS regulations.

        Args:
            trip_data: Dictionary containing trip information:
                - total_distance_miles: Trip distance in miles
                - estimated_driving_hours: Estimated driving time
                - pickup_location: Pickup location
                - dropoff_location: Dropoff location
            driver_status: Dictionary containing current driver HOS status:
                - current_cycle_hours: Hours used in 8-day cycle
                - current_duty_period_hours: Hours on duty in current period
                - current_driving_hours: Hours driven in current period
                - hours_since_last_break: Hours since last 30-min break

        Returns:
            Dict containing comprehensive compliance validation results
        """
        try:
            self.logger.info(
                f"Validating trip compliance for {trip_data.get('total_distance_miles', 0)} mile trip"
            )

            # Extract and validate inputs
            distance = Decimal(str(trip_data.get("total_distance_miles", 0)))
            driving_hours = Decimal(str(trip_data.get("estimated_driving_hours", 0)))

            current_cycle = Decimal(str(driver_status.get("current_cycle_hours", 0)))
            current_duty = Decimal(
                str(driver_status.get("current_duty_period_hours", 0))
            )
            current_driving = Decimal(
                str(driver_status.get("current_driving_hours", 0))
            )
            hours_since_break = Decimal(
                str(driver_status.get("hours_since_last_break", 0))
            )

            # Validate driver can start trip
            can_start, start_issues = self._validate_trip_start_eligibility(
                current_cycle, current_duty, current_driving, hours_since_break
            )

            # Calculate HOS impact of trip
            hos_impact = self.hos_calculator.calculate_cycle_hours_for_trip(
                driving_hours, current_cycle
            )

            # Plan required breaks
            break_plan = self.break_planner.plan_trip_breaks(
                distance,
                driving_hours,
                current_cycle,
                current_duty,
                current_driving,
                hours_since_break,
            )

            # Validate overall compliance
            overall_compliance = self._validate_overall_compliance(
                hos_impact, break_plan, driver_status
            )

            # Generate recommendations
            recommendations = self._generate_compliance_recommendations(
                can_start, start_issues, hos_impact, break_plan
            )

            # Calculate compliance score
            compliance_score = self._calculate_overall_compliance_score(
                can_start, overall_compliance, break_plan["compliance"]
            )

            result = {
                "is_compliant": can_start and overall_compliance["is_compliant"],
                "compliance_score": compliance_score,
                "can_start_trip": can_start,
                "start_eligibility": {"eligible": can_start, "issues": start_issues},
                "hos_impact": hos_impact,
                "break_plan": break_plan,
                "overall_compliance": overall_compliance,
                "recommendations": recommendations,
                "trip_summary": {
                    "total_distance_miles": float(distance),
                    "estimated_driving_hours": float(driving_hours),
                    "total_trip_time_hours": break_plan["total_trip_time_hours"],
                    "required_breaks": break_plan["total_breaks"],
                },
                "validated_at": timezone.now().isoformat(),
            }

            self.logger.info(
                f"Trip compliance validation completed: {'COMPLIANT' if result['is_compliant'] else 'NON-COMPLIANT'}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Trip compliance validation failed: {str(e)}")
            raise ComplianceValidationError(
                f"Failed to validate trip compliance: {str(e)}"
            )

    def validate_driver_eligibility(
        self, driver_status: Dict, required_driving_hours: Optional[Decimal] = None
    ) -> Dict:
        """
        Validate driver eligibility to start driving.

        Args:
            driver_status: Current driver HOS status
            required_driving_hours: Optional required driving time to check

        Returns:
            Dict containing driver eligibility validation
        """
        try:
            current_cycle = Decimal(str(driver_status.get("current_cycle_hours", 0)))
            current_duty = Decimal(
                str(driver_status.get("current_duty_period_hours", 0))
            )
            current_driving = Decimal(
                str(driver_status.get("current_driving_hours", 0))
            )
            hours_since_break = Decimal(
                str(driver_status.get("hours_since_last_break", 0))
            )

            # Calculate available hours
            availability = self.hos_calculator.calculate_available_hours(
                current_cycle, current_duty, current_driving, hours_since_break
            )

            # Validate current status
            current_compliance = self.hos_calculator.validate_hos_compliance(
                current_cycle, current_duty, current_driving, hours_since_break
            )

            # Check specific driving requirement if provided
            can_complete_required_driving = True
            required_driving_issues = []

            if required_driving_hours:
                max_continuous = Decimal(
                    str(availability["max_continuous_driving_hours"])
                )
                if required_driving_hours > max_continuous:
                    can_complete_required_driving = False
                    required_driving_issues.append(
                        {
                            "issue": "insufficient_available_hours",
                            "description": f"Required {required_driving_hours}h driving, only {max_continuous}h available",
                            "required_hours": float(required_driving_hours),
                            "available_hours": float(max_continuous),
                        }
                    )

            # Calculate required rest if not eligible
            required_rest = None
            if not availability["can_drive"]:
                required_rest = self.hos_calculator.calculate_required_rest(
                    current_cycle,
                    current_duty,
                    current_driving,
                    hours_since_break >= self.hos_calculator.BREAK_REQUIRED_AFTER_HOURS,
                )

            return {
                "is_eligible": availability["can_drive"]
                and can_complete_required_driving,
                "can_drive_now": availability["can_drive"],
                "can_complete_required_driving": can_complete_required_driving,
                "violation_reason": availability["violation_reason"],
                "available_hours": availability["available_hours"],
                "current_compliance": current_compliance,
                "required_driving_issues": required_driving_issues,
                "required_rest": required_rest,
                "max_continuous_driving_hours": availability[
                    "max_continuous_driving_hours"
                ],
                "validated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Driver eligibility validation failed: {str(e)}")
            raise ComplianceValidationError(
                f"Failed to validate driver eligibility: {str(e)}"
            )

    def validate_route_compliance(self, route_data: Dict, driver_status: Dict) -> Dict:
        """
        Validate route compliance with HOS regulations.

        Args:
            route_data: Route information including waypoints and stops
            driver_status: Current driver HOS status

        Returns:
            Dict containing route compliance validation
        """
        try:
            # Extract route information
            total_distance = Decimal(str(route_data.get("total_distance_miles", 0)))
            estimated_time = Decimal(
                str(route_data.get("estimated_driving_time_hours", 0))
            )
            waypoints = route_data.get("waypoints", [])

            # Validate basic route feasibility
            route_feasibility = self._validate_route_feasibility(
                total_distance, estimated_time
            )

            # Check HOS compliance for route
            trip_compliance = self.validate_trip_compliance(
                {
                    "total_distance_miles": total_distance,
                    "estimated_driving_hours": estimated_time,
                },
                driver_status,
            )

            # Validate waypoints if provided
            waypoint_compliance = self._validate_waypoint_compliance(waypoints)

            # Check for adverse driving conditions considerations
            adverse_conditions = self._check_adverse_driving_conditions(route_data)

            return {
                "is_compliant": (
                    route_feasibility["is_feasible"]
                    and trip_compliance["is_compliant"]
                    and waypoint_compliance["is_compliant"]
                ),
                "route_feasibility": route_feasibility,
                "trip_compliance": trip_compliance,
                "waypoint_compliance": waypoint_compliance,
                "adverse_conditions": adverse_conditions,
                "route_summary": {
                    "total_distance_miles": float(total_distance),
                    "estimated_driving_hours": float(estimated_time),
                    "number_of_waypoints": len(waypoints),
                },
                "validated_at": timezone.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Route compliance validation failed: {str(e)}")
            raise ComplianceValidationError(
                f"Failed to validate route compliance: {str(e)}"
            )

    def generate_compliance_report(
        self, trip_data: Dict, driver_status: Dict, route_data: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive compliance report.

        Args:
            trip_data: Trip information
            driver_status: Driver HOS status
            route_data: Optional route information

        Returns:
            Dict containing comprehensive compliance report
        """
        try:
            self.logger.info("Generating comprehensive compliance report")

            # Validate trip compliance
            trip_validation = self.validate_trip_compliance(trip_data, driver_status)

            # Validate driver eligibility
            driver_validation = self.validate_driver_eligibility(driver_status)

            # Validate route if provided
            route_validation = None
            if route_data:
                route_validation = self.validate_route_compliance(
                    route_data, driver_status
                )

            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                trip_validation, driver_validation, route_validation
            )

            # Generate detailed findings
            detailed_findings = self._generate_detailed_findings(
                trip_validation, driver_validation, route_validation
            )

            # Generate action items
            action_items = self._generate_action_items(
                trip_validation, driver_validation, route_validation
            )

            report = {
                "report_id": f"compliance_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                "generated_at": timezone.now().isoformat(),
                "executive_summary": executive_summary,
                "trip_validation": trip_validation,
                "driver_validation": driver_validation,
                "route_validation": route_validation,
                "detailed_findings": detailed_findings,
                "action_items": action_items,
                "report_metadata": {
                    "validator_version": "1.0",
                    "regulations_version": "FMCSA 395 (April 2022)",
                    "validation_scope": "property_carrying_cmv",
                },
            }

            self.logger.info("Compliance report generated successfully")
            return report

        except Exception as e:
            self.logger.error(f"Compliance report generation failed: {str(e)}")
            raise ComplianceValidationError(
                f"Failed to generate compliance report: {str(e)}"
            )

    def _validate_trip_start_eligibility(
        self,
        current_cycle: Decimal,
        current_duty: Decimal,
        current_driving: Decimal,
        hours_since_break: Decimal,
    ) -> Tuple[bool, List[Dict]]:
        """Validate if driver is eligible to start the trip."""
        issues = []

        # Check cycle hours limit
        if current_cycle >= self.hos_calculator.MAX_CYCLE_HOURS:
            issues.append(
                {
                    "type": "cycle_limit_reached",
                    "description": "70-hour/8-day cycle limit reached",
                    "current_hours": float(current_cycle),
                    "limit": 70,
                    "required_action": "34-hour restart required",
                }
            )

        # Check duty period limit
        if current_duty >= self.hos_calculator.MAX_DUTY_PERIOD_HOURS:
            issues.append(
                {
                    "type": "duty_period_limit_reached",
                    "description": "14-hour duty period limit reached",
                    "current_hours": float(current_duty),
                    "limit": 14,
                    "required_action": "10 hours off duty required",
                }
            )

        # Check driving limit
        if current_driving >= self.hos_calculator.MAX_DRIVING_HOURS:
            issues.append(
                {
                    "type": "driving_limit_reached",
                    "description": "11-hour driving limit reached",
                    "current_hours": float(current_driving),
                    "limit": 11,
                    "required_action": "10 hours off duty required",
                }
            )

        # Check 30-minute break requirement
        if hours_since_break >= self.hos_calculator.BREAK_REQUIRED_AFTER_HOURS:
            issues.append(
                {
                    "type": "break_required",
                    "description": "30-minute break required after 8 hours driving",
                    "current_hours": float(hours_since_break),
                    "limit": 8,
                    "required_action": "30-minute break required",
                }
            )

        return len(issues) == 0, issues

    def _validate_overall_compliance(
        self, hos_impact: Dict, break_plan: Dict, driver_status: Dict
    ) -> Dict:
        """Validate overall trip compliance."""
        issues = []
        warnings = []

        # Check if trip exceeds cycle limit
        if hos_impact.get("exceeds_cycle_limit", False):
            issues.append(
                {
                    "type": "exceeds_cycle_limit",
                    "description": "Trip would exceed 70-hour/8-day limit",
                    "hours_over": hos_impact.get("hours_over_limit", 0),
                }
            )

        # Check break plan compliance
        if not break_plan["compliance"]["is_compliant"]:
            for issue in break_plan["compliance"]["issues"]:
                issues.append(
                    {
                        "type": "break_plan_issue",
                        "description": issue["description"],
                        "issue_type": issue["type"],
                    }
                )

        # Check for excessive trip time
        total_time = break_plan.get("total_trip_time_hours", 0)
        if total_time > 24:
            warnings.append(
                {
                    "type": "long_trip_duration",
                    "description": f"Trip duration ({total_time:.1f} hours) exceeds 24 hours",
                    "total_hours": total_time,
                }
            )

        return {
            "is_compliant": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_issues": len(issues),
            "total_warnings": len(warnings),
        }

    def _generate_compliance_recommendations(
        self,
        can_start: bool,
        start_issues: List[Dict],
        hos_impact: Dict,
        break_plan: Dict,
    ) -> List[Dict]:
        """Generate compliance recommendations."""
        recommendations = []

        if not can_start:
            for issue in start_issues:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "pre_trip",
                        "title": "Address Start Eligibility Issue",
                        "description": issue["description"],
                        "action": issue.get("required_action", "Contact dispatch"),
                        "regulation": "HOS Pre-Trip Requirements",
                    }
                )

        if hos_impact.get("requires_34_hour_restart", False):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "planning",
                    "title": "34-Hour Restart Required",
                    "description": "Trip requires 34-hour restart before beginning",
                    "action": "Schedule 34 consecutive hours off duty before trip",
                    "regulation": "395.3(c)",
                }
            )

        if break_plan["total_breaks"] > 3:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "planning",
                    "title": "Multiple Breaks Required",
                    "description": f'Trip requires {break_plan["total_breaks"]} breaks',
                    "action": "Plan break locations and timing in advance",
                    "regulation": "HOS Break Planning",
                }
            )

        # Add fuel planning recommendation
        if break_plan["fuel_stops_count"] > 0:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "operational",
                    "title": "Fuel Stop Planning",
                    "description": f'Plan {break_plan["fuel_stops_count"]} fuel stops',
                    "action": "Identify fuel stops along route every 1000 miles",
                    "regulation": "Operational Requirement",
                }
            )

        return recommendations

    def _calculate_overall_compliance_score(
        self, can_start: bool, overall_compliance: Dict, break_compliance: Dict
    ) -> int:
        """Calculate overall compliance score."""
        score = 100

        if not can_start:
            score -= 30

        if not overall_compliance["is_compliant"]:
            score -= overall_compliance["total_issues"] * 15

        score -= overall_compliance.get("total_warnings", 0) * 5
        score -= (100 - break_compliance.get("compliance_score", 100)) * 0.2

        return max(0, min(100, int(score)))

    def _validate_route_feasibility(self, distance: Decimal, time: Decimal) -> Dict:
        """Validate basic route feasibility."""
        issues = []

        if distance <= 0:
            issues.append("Invalid route distance")
        if time <= 0:
            issues.append("Invalid route time")

        # Check reasonable speed
        if distance > 0 and time > 0:
            speed = float(distance) / float(time)
            if speed < 20:
                issues.append(f"Average speed too low: {speed:.1f} mph")
            elif speed > 80:
                issues.append(f"Average speed too high: {speed:.1f} mph")

        return {"is_feasible": len(issues) == 0, "issues": issues}

    def _validate_waypoint_compliance(self, waypoints: List[Dict]) -> Dict:
        """Validate waypoint compliance."""
        # Basic validation - can be extended
        return {"is_compliant": True, "issues": [], "waypoint_count": len(waypoints)}

    def _check_adverse_driving_conditions(self, route_data: Dict) -> Dict:
        """Check for adverse driving conditions considerations."""
        # This would integrate with weather/traffic APIs
        return {
            "conditions_considered": False,
            "additional_time_allowance": 0,
            "recommendations": [],
        }

    def _generate_executive_summary(
        self,
        trip_validation: Dict,
        driver_validation: Dict,
        route_validation: Optional[Dict],
    ) -> Dict:
        """Generate executive summary of compliance status."""
        overall_compliant = (
            trip_validation["is_compliant"] and driver_validation["is_eligible"]
        )

        if route_validation:
            overall_compliant = overall_compliant and route_validation["is_compliant"]

        key_findings = []
        if not driver_validation["is_eligible"]:
            key_findings.append("Driver not eligible to start trip")
        if not trip_validation["is_compliant"]:
            key_findings.append("Trip plan not HOS compliant")
        if route_validation and not route_validation["is_compliant"]:
            key_findings.append("Route not compliant with HOS regulations")

        return {
            "overall_compliant": overall_compliant,
            "compliance_score": trip_validation["compliance_score"],
            "key_findings": key_findings,
            "total_breaks_required": trip_validation["break_plan"]["total_breaks"],
            "trip_duration_hours": trip_validation["trip_summary"][
                "total_trip_time_hours"
            ],
        }

    def _generate_detailed_findings(
        self,
        trip_validation: Dict,
        driver_validation: Dict,
        route_validation: Optional[Dict],
    ) -> Dict:
        """Generate detailed findings section."""
        return {
            "hos_analysis": {
                "cycle_status": driver_validation["current_compliance"],
                "trip_impact": trip_validation["hos_impact"],
                "break_requirements": trip_validation["break_plan"],
            },
            "regulatory_compliance": {
                "applicable_regulations": [
                    "395.3(a)(2) - 14 hour rule",
                    "395.3(a)(3) - 11 hour rule",
                    "395.3(b) - 70 hour rule",
                    "395.3(a)(3)(ii) - 30 minute break",
                ],
                "compliance_status": trip_validation["is_compliant"],
            },
        }

    def _generate_action_items(
        self,
        trip_validation: Dict,
        driver_validation: Dict,
        route_validation: Optional[Dict],
    ) -> List[Dict]:
        """Generate action items from validation results."""
        actions = []

        # Add recommendations as action items
        for rec in trip_validation.get("recommendations", []):
            actions.append(
                {
                    "priority": rec["priority"],
                    "category": rec["category"],
                    "description": rec["description"],
                    "action_required": rec["action"],
                    "deadline": "Before trip start",
                    "responsible_party": "Driver/Dispatcher",
                }
            )

        return actions


    def get_compliance_recommendations(self, hos_status) -> List[Dict]:
        """
        Get compliance recommendations for a given HOS status.
        
        Args:
            hos_status: HOSStatus model instance
            
        Returns:
            List of recommendation dictionaries
        """
        try:
            recommendations = []
            
            # Check if driver can't drive
            if not hos_status.can_drive:
                if hos_status.needs_30_minute_break:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'immediate',
                        'title': '30-Minute Break Required',
                        'description': '30-minute rest break required before continuing to drive',
                        'action': 'Take 30 consecutive minutes off duty or in sleeper berth',
                        'regulation': '395.3(a)(3)(ii)'
                    })
                
                if hos_status.available_driving_hours <= 0:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'daily_limits',
                        'title': '11-Hour Driving Limit Reached',
                        'description': '11-hour daily driving limit has been reached',
                        'action': 'Take 10 consecutive hours off duty to reset daily limits',
                        'regulation': '395.3(a)(3)'
                    })
                
                if hos_status.available_duty_period_hours <= 0:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'daily_limits',
                        'title': '14-Hour Window Limit Reached',
                        'description': '14-hour duty period limit has been reached',
                        'action': 'Take 10 consecutive hours off duty to reset duty period',
                        'regulation': '395.3(a)(2)'
                    })
                
                if hos_status.available_cycle_hours <= 0:
                    recommendations.append({
                        'priority': 'high',
                        'category': 'weekly_limits',
                        'title': '70-Hour Cycle Limit Reached',
                        'description': '70-hour/8-day cycle limit has been reached',
                        'action': 'Take 34 consecutive hours off duty to restart cycle',
                        'regulation': '395.3(c)'
                    })
            
            # Warning recommendations for approaching limits
            if hos_status.can_drive:
                if hos_status.available_driving_hours <= 2:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'planning',
                        'title': 'Approaching Driving Limit',
                        'description': f'Only {hos_status.available_driving_hours} hours of driving time remaining',
                        'action': 'Plan route to destination within available hours',
                        'regulation': '395.3(a)(3)'
                    })
                
                if hos_status.available_cycle_hours <= 10:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'planning',
                        'title': 'Approaching Cycle Limit',
                        'description': f'Only {hos_status.available_cycle_hours} hours remaining in 8-day cycle',
                        'action': 'Consider scheduling 34-hour restart after current trip',
                        'regulation': '395.3(c)'
                    })
                
                if hos_status.hours_since_last_break >= 6:
                    recommendations.append({
                        'priority': 'medium',
                        'category': 'immediate',
                        'title': 'Break Needed Soon',
                        'description': f'30-minute break will be required after {8 - hos_status.hours_since_last_break} more hours of driving',
                        'action': 'Plan break location for upcoming 30-minute rest requirement',
                        'regulation': '395.3(a)(3)(ii)'
                    })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance recommendations: {str(e)}")
            return [{
                'priority': 'low',
                'category': 'system',
                'title': 'Unable to Generate Recommendations',
                'description': 'System error occurred while analyzing compliance status',
                'action': 'Contact dispatch for manual compliance review',
                'regulation': ''
            }]


class ComplianceValidationError(Exception):
    """Exception raised when compliance validation fails."""

    pass
