"""
HOS Compliance Services Package.

This package contains all business logic services for Hours of Service
compliance validation, calculation, and planning.

Services:
- HOSCalculatorService: Core HOS calculations and rule validation
- ComplianceValidatorService: Trip compliance validation
- RestBreakPlannerService: Mandatory rest break planning
"""

from .hos_calculator import HOSCalculatorService
from .compliance_validator import ComplianceValidatorService
from .rest_break_planner import RestBreakPlannerService

__all__ = [
    'HOSCalculatorService',
    'ComplianceValidatorService', 
    'RestBreakPlannerService'
]
