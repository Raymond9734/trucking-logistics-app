"""
ELD Logs API Serializers.

Provides serialization and validation for ELD logs API endpoints.
Handles input validation, data formatting, and response serialization
for all ELD-related API operations including daily logs, duty status
records, and log sheet generation.
"""

from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date, time
from .models import DailyLog, DutyStatusRecord, LogSheet


class DailyLogSerializer(serializers.ModelSerializer):
    """
    Serializer for DailyLog model.
    
    Provides complete daily log information including all required
    FMCSA fields and calculated totals for ELD compliance.
    """
    
    trip_id = serializers.UUIDField(source='trip.id', read_only=True)
    duty_status_summary = serializers.SerializerMethodField()
    certification_status = serializers.SerializerMethodField()
    compliance_violations = serializers.SerializerMethodField()
    is_complete = serializers.ReadOnlyField()
    total_hours_sum = serializers.ReadOnlyField()
    
    class Meta:
        model = DailyLog
        fields = [
            'id',
            'trip_id',
            'log_date',
            'driver_name',
            'co_driver_name', 
            'carrier_name',
            'carrier_main_office_address',
            'vehicle_number',
            'trailer_number',
            'total_miles_driving_today',
            'total_hours_off_duty',
            'total_hours_sleeper_berth',
            'total_hours_driving',
            'total_hours_on_duty_not_driving',
            'period_start_time',
            'shipping_document_numbers',
            'is_certified',
            'driver_signature_date',
            'remarks',
            'created_at',
            'updated_at',
            'duty_status_summary',
            'certification_status',
            'compliance_violations',
            'is_complete',
            'total_hours_sum',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at', 
            'duty_status_summary',
            'certification_status',
            'compliance_violations',
            'is_complete',
            'total_hours_sum',
        ]
    
    def get_duty_status_summary(self, obj):
        """Get summary of duty status hours."""
        return obj.get_duty_status_summary()
    
    def get_certification_status(self, obj):
        """Get certification status information."""
        return obj.get_certification_status()
    
    def get_compliance_violations(self, obj):
        """Get compliance validation results."""
        return obj.validate_compliance()


class DailyLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new daily logs.
    
    Validates required fields for daily log creation
    and ensures compliance with FMCSA regulations.
    """
    
    trip_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = DailyLog
        fields = [
            'trip_id',
            'log_date',
            'driver_name',
            'co_driver_name',
            'carrier_name', 
            'carrier_main_office_address',
            'vehicle_number',
            'trailer_number',
            'period_start_time',
            'shipping_document_numbers',
            'remarks'
        ]
    
    def validate_log_date(self, value):
        """Validate log date is not in the future."""
        if value > date.today():
            raise serializers.ValidationError("Log date cannot be in the future")
        return value


class DutyStatusRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for DutyStatusRecord model.
    
    Handles individual duty status change records within
    a daily log for detailed ELD tracking.
    """
    
    daily_log_id = serializers.UUIDField(source='daily_log.id', read_only=True)
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = DutyStatusRecord
        fields = [
            'id',
            'daily_log_id',
            'sequence_number',
            'duty_status',
            'duty_status_display',
            'start_time',
            'end_time',
            'duration_minutes',
            'duration_hours',
            'location',
            'odometer_reading',
            'engine_hours',
            'remarks',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 
            'duty_status_display',
            'duration_hours',
            'created_at',
            'updated_at'
        ]
    
    def get_duration_hours(self, obj):
        """Convert duration from minutes to hours."""
        return round(obj.duration_minutes / 60, 2) if obj.duration_minutes else 0
    
    def validate(self, data):
        """Validate duty status record data."""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
            
            # Calculate duration in minutes
            duration = (end_time - start_time).total_seconds() / 60
            if duration > 24 * 60:  # More than 24 hours
                raise serializers.ValidationError({
                    'end_time': 'Duty status record cannot exceed 24 hours'
                })
        
        return data


class LogSheetSerializer(serializers.ModelSerializer):
    """
    Serializer for LogSheet model.
    
    Handles log sheet generation and visual representation
    of daily logs in the required FMCSA format.
    """
    
    daily_log_id = serializers.UUIDField(source='daily_log.id', read_only=True)
    grid_data = serializers.JSONField(read_only=True)
    
    class Meta:
        model = LogSheet
        fields = [
            'id',
            'daily_log_id',
            'sheet_format',
            'grid_data',
            'pdf_content',
            'is_generated',
            'generated_at',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'grid_data',
            'is_generated',
            'generated_at',
            'created_at'
        ]


class ELDLogsGenerationRequestSerializer(serializers.Serializer):
    """
    Serializer for ELD logs generation requests.
    
    Validates input for generating ELD logs for a trip
    with specified parameters and date range.
    """
    
    trip_id = serializers.UUIDField(
        required=True,
        help_text="Trip ID for which to generate ELD logs"
    )
    
    start_date = serializers.DateField(
        required=True,
        help_text="Start date for log generation"
    )
    
    end_date = serializers.DateField(
        required=False,
        help_text="End date for log generation (defaults to start_date)"
    )
    
    include_log_sheets = serializers.BooleanField(
        default=True,
        help_text="Whether to generate visual log sheets"
    )
    
    sheet_format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('json', 'JSON')],
        default='pdf',
        help_text="Format for generated log sheets"
    )
    
    def validate(self, data):
        """Validate date range for log generation."""
        start_date = data['start_date']
        end_date = data.get('end_date', start_date)
        
        if end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'End date cannot be before start date'
            })
        
        # Limit to reasonable date range
        date_diff = (end_date - start_date).days
        if date_diff > 31:  # More than 1 month
            raise serializers.ValidationError(
                'Date range cannot exceed 31 days'
            )
        
        data['end_date'] = end_date
        return data


class ELDLogsGenerationResponseSerializer(serializers.Serializer):
    """
    Serializer for ELD logs generation responses.
    
    Provides results of ELD log generation including
    created logs, any errors, and summary statistics.
    """
    
    trip_id = serializers.UUIDField()
    generated_logs = DailyLogSerializer(many=True)
    generated_log_sheets = LogSheetSerializer(many=True)
    generation_summary = serializers.DictField()
    errors = serializers.ListField(
        child=serializers.CharField(),
        default=list
    )
    warnings = serializers.ListField(
        child=serializers.CharField(), 
        default=list
    )
    generated_at = serializers.DateTimeField()


class LogCertificationSerializer(serializers.Serializer):
    """
    Serializer for log certification requests.
    
    Handles driver certification of daily logs
    with electronic signature capability.
    """
    
    daily_log_id = serializers.UUIDField(
        required=True,
        help_text="Daily log ID to certify"
    )
    
    driver_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Driver's full legal name for certification"
    )
    
    certification_statement = serializers.CharField(
        default="I certify that these entries are true and correct",
        help_text="Certification statement"
    )
    
    electronic_signature = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Electronic signature (driver initials or full name)"
    )


class DutyStatusUpdateRequestSerializer(serializers.Serializer):
    """
    Serializer for duty status update requests.
    
    Handles real-time duty status changes and creates
    corresponding duty status records.
    """
    
    daily_log_id = serializers.UUIDField(
        required=True,
        help_text="Daily log to update"
    )
    
    new_duty_status = serializers.ChoiceField(
        choices=DutyStatusRecord.DutyStatus.choices,
        required=True,
        help_text="New duty status"
    )
    
    change_time = serializers.DateTimeField(
        default=timezone.now,
        help_text="Time of duty status change"
    )
    
    location = serializers.CharField(
        max_length=200,
        required=True,
        help_text="Location where status change occurred (city, state)"
    )
    
    odometer_reading = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Current odometer reading"
    )
    
    engine_hours = serializers.DecimalField(
        max_digits=8,
        decimal_places=1,
        required=False,
        min_value=0,
        help_text="Current engine hours"
    )
    
    remarks = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Additional remarks"
    )


class ELDComplianceReportSerializer(serializers.Serializer):
    """
    Serializer for ELD compliance reports.
    
    Provides comprehensive ELD compliance reporting
    including log completeness, violations, and metrics.
    """
    
    trip_id = serializers.UUIDField()
    driver_name = serializers.CharField()
    report_period_start = serializers.DateField()
    report_period_end = serializers.DateField()
    
    daily_logs = DailyLogSerializer(many=True)
    total_logs = serializers.IntegerField()
    certified_logs = serializers.IntegerField()
    incomplete_logs = serializers.IntegerField()
    
    compliance_summary = serializers.DictField()
    violations = serializers.ListField(child=serializers.DictField())
    recommendations = serializers.ListField(child=serializers.CharField())
    
    report_generated_at = serializers.DateTimeField()


class LogSheetGridSerializer(serializers.Serializer):
    """
    Serializer for log sheet grid data.
    
    Handles the visual representation of duty status
    on the FMCSA-compliant grid format.
    """
    
    date = serializers.DateField()
    period_start_time = serializers.TimeField()
    grid_hours = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=23),
        help_text="24-hour period hours (0-23)"
    )
    
    off_duty_periods = serializers.ListField(
        child=serializers.DictField(),
        help_text="Off duty time periods"
    )
    
    sleeper_berth_periods = serializers.ListField(
        child=serializers.DictField(),
        help_text="Sleeper berth time periods"
    )
    
    driving_periods = serializers.ListField(
        child=serializers.DictField(),
        help_text="Driving time periods"
    )
    
    on_duty_not_driving_periods = serializers.ListField(
        child=serializers.DictField(), 
        help_text="On duty not driving time periods"
    )
    
    remarks = serializers.ListField(
        child=serializers.DictField(),
        help_text="Remarks with timestamps and locations"
    )
    
    totals = serializers.DictField(
        help_text="Total hours for each duty status"
    )


class BulkLogOperationSerializer(serializers.Serializer):
    """
    Serializer for bulk log operations.
    
    Handles operations on multiple logs simultaneously
    such as bulk certification or bulk generation.
    """
    
    trip_id = serializers.UUIDField(required=True)
    operation = serializers.ChoiceField(
        choices=[
            ('certify', 'Certify Logs'),
            ('generate', 'Generate Logs'),
            ('recalculate', 'Recalculate Totals'),
            ('validate', 'Validate Compliance')
        ],
        required=True
    )
    
    date_range = serializers.DictField(
        child=serializers.DateField(),
        required=False,
        help_text="Date range for bulk operation (start_date, end_date)"
    )
    
    log_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific log IDs for operation"
    )
    
    parameters = serializers.DictField(
        required=False,
        help_text="Additional parameters for the operation"
    )


class BulkLogOperationResponseSerializer(serializers.Serializer):
    """
    Serializer for bulk log operation responses.
    
    Provides results of bulk operations on multiple logs.
    """
    
    operation = serializers.CharField()
    total_logs_processed = serializers.IntegerField()
    successful_operations = serializers.IntegerField()
    failed_operations = serializers.IntegerField()
    
    results = serializers.ListField(
        child=serializers.DictField(),
        help_text="Detailed results for each log"
    )
    
    errors = serializers.ListField(
        child=serializers.DictField(),
        help_text="Errors encountered during processing"
    )
    
    summary = serializers.DictField()
    processed_at = serializers.DateTimeField()
