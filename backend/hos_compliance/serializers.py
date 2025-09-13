"""
HOS Compliance API Serializers.

Provides serialization and validation for HOS compliance API endpoints.
Handles input validation, data formatting, and response serialization
for all HOS-related API operations.
"""

from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from .models import HOSStatus, RestBreak, ComplianceViolation
from .services.hos_calculator import HOSCalculatorService


class HOSStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for HOSStatus model.
    
    Provides complete HOS status information including available hours,
    compliance status, and next required actions.
    """
    
    trip_id = serializers.UUIDField(source='trip.id', read_only=True)
    driver_name = serializers.CharField(source='trip.driver_name', read_only=True)
    status_summary = serializers.SerializerMethodField()
    max_continuous_driving_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = HOSStatus
        fields = [
            'id', 
            'trip_id',
            'driver_name',
            'current_cycle_hours',
            'available_cycle_hours', 
            'current_duty_period_hours',
            'available_duty_period_hours',
            'current_driving_hours',
            'available_driving_hours',
            'last_duty_status_change',
            'current_duty_status',
            'hours_since_last_break',
            'needs_30_minute_break',
            'can_drive',
            'violation_reason',
            'next_required_rest_hours',
            'calculated_at',
            'status_summary',
            'max_continuous_driving_hours',
        ]
        read_only_fields = [
            'id',
            'calculated_at', 
            'status_summary',
            'max_continuous_driving_hours'
        ]
    
    def get_status_summary(self, obj):
        """Get comprehensive status summary."""
        return obj.get_status_summary()
    
    def get_max_continuous_driving_hours(self, obj):
        """Get maximum continuous driving hours."""
        return float(obj.get_maximum_continuous_driving_hours())


class HOSCalculationRequestSerializer(serializers.Serializer):
    """
    Serializer for HOS calculation requests.
    
    Validates input data for HOS calculations and provides
    clean data for service layer processing.
    """
    
    current_cycle_hours = serializers.DecimalField(
        max_digits=4, 
        decimal_places=1,
        min_value=0,
        max_value=80,  # Allow slight over for validation
        required=True,
        help_text="Current hours used in 8-day cycle"
    )
    
    current_duty_period_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=1, 
        min_value=0,
        max_value=24,
        default=0,
        help_text="Hours on duty in current 14-hour window"
    )
    
    current_driving_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=0, 
        max_value=24,
        default=0,
        help_text="Hours driven in current duty period"
    )
    
    hours_since_last_break = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        min_value=0,
        max_value=24,
        default=0,
        help_text="Hours driven since last 30-minute break"
    )
    
    def validate(self, data):
        """Cross-field validation for HOS calculation data."""
        
        current_duty_period = data.get('current_duty_period_hours', 0)
        current_driving = data.get('current_driving_hours', 0)
        
        # Driving hours cannot exceed duty period hours
        if current_driving > current_duty_period:
            raise serializers.ValidationError({
                'current_driving_hours': 'Driving hours cannot exceed duty period hours'
            })
        
        return data


class HOSCalculationResponseSerializer(serializers.Serializer):
    """
    Serializer for HOS calculation responses.
    
    Formats calculation results from HOSCalculatorService 
    for API response.
    """
    
    can_drive = serializers.BooleanField()
    violation_reason = serializers.CharField(allow_blank=True)
    available_hours = serializers.DictField()
    limits = serializers.DictField() 
    current_usage = serializers.DictField()
    max_continuous_driving_hours = serializers.DecimalField(max_digits=4, decimal_places=1)
    calculated_at = serializers.DateTimeField()


class DutyStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for duty status updates.
    
    Handles updating driver duty status and recalculating
    HOS compliance based on new status.
    """
    
    trip_id = serializers.UUIDField(
        required=True,
        help_text="Trip ID for the HOS status to update"
    )
    
    new_duty_status = serializers.ChoiceField(
        choices=HOSStatus.DutyStatus.choices,
        required=True,
        help_text="New duty status for the driver"
    )
    
    location = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Location where duty status changed"
    )
    
    remarks = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True, 
        help_text="Additional remarks about status change"
    )


class RestBreakSerializer(serializers.ModelSerializer):
    """
    Serializer for RestBreak model.
    
    Handles rest break tracking and validation
    for HOS compliance.
    """
    
    trip_id = serializers.UUIDField(source='trip.id', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = RestBreak
        fields = [
            'id',
            'trip_id', 
            'break_type',
            'start_time',
            'end_time',
            'duration_minutes',
            'duration_hours',
            'location',
            'is_compliant',
            'remarks',
            'created_at'
        ]
        read_only_fields = ['id', 'duration_hours', 'created_at']
    
    def get_duration_hours(self, obj):
        """Convert duration from minutes to hours."""
        return round(obj.duration_minutes / 60, 2) if obj.duration_minutes else 0


class ComplianceViolationSerializer(serializers.ModelSerializer):
    """
    Serializer for ComplianceViolation model.
    
    Provides violation information for compliance tracking
    and reporting.
    """
    
    trip_id = serializers.UUIDField(source='trip.id', read_only=True)
    driver_name = serializers.CharField(source='trip.driver_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = ComplianceViolation
        fields = [
            'id',
            'trip_id',
            'driver_name', 
            'violation_type',
            'severity',
            'severity_display',
            'description',
            'regulation_reference',
            'occurred_at',
            'detected_at',
            'is_resolved',
            'resolution_notes',
            'created_at'
        ]
        read_only_fields = [
            'id', 
            'severity_display',
            'detected_at', 
            'created_at'
        ]


class ComplianceViolationListSerializer(serializers.Serializer):
    """
    Serializer for listing compliance violations with filtering.
    
    Provides filtering and summary information for 
    compliance violation listings.
    """
    
    trip_id = serializers.UUIDField(required=False)
    severity = serializers.ChoiceField(
        choices=ComplianceViolation.Severity.choices,
        required=False
    )
    is_resolved = serializers.BooleanField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)


class HOSComplianceReportSerializer(serializers.Serializer):
    """
    Serializer for HOS compliance reports.
    
    Provides comprehensive compliance reporting data
    including violations, status, and recommendations.
    """
    
    trip_id = serializers.UUIDField()
    driver_name = serializers.CharField()
    current_status = HOSStatusSerializer()
    violations = ComplianceViolationSerializer(many=True)
    rest_breaks = RestBreakSerializer(many=True)
    compliance_score = serializers.IntegerField()
    recommendations = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of recommended actions for compliance"
    )
    report_generated_at = serializers.DateTimeField()


class TripHOSPlanningSerializer(serializers.Serializer):
    """
    Serializer for trip HOS planning requests.
    
    Handles planning HOS compliance for upcoming trips
    based on estimated driving time and current status.
    """
    
    estimated_driving_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=0,
        max_value=24,
        required=True,
        help_text="Estimated driving time for the trip"
    )
    
    current_cycle_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=0,
        max_value=80,
        required=True,
        help_text="Current hours used in 8-day cycle"
    )
    
    planned_start_time = serializers.DateTimeField(
        required=False,
        help_text="Planned trip start time"
    )


class TripHOSPlanningResponseSerializer(serializers.Serializer):
    """
    Serializer for trip HOS planning responses.
    
    Provides trip planning analysis including feasibility,
    required breaks, and optimal scheduling.
    """
    
    is_trip_feasible = serializers.BooleanField()
    total_trip_time_estimate = serializers.DecimalField(max_digits=4, decimal_places=1)
    required_breaks = serializers.ListField(child=serializers.DictField())
    recommended_start_time = serializers.DateTimeField()
    cycle_impact = serializers.DictField()
    warnings = serializers.ListField(child=serializers.CharField())
    calculated_at = serializers.DateTimeField()
