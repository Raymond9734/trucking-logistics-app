"""
ELD Logs API Views.

Provides REST API endpoints for ELD log management, daily log generation,
duty status tracking, and log sheet creation. Integrates with existing
service layer for business logic processing.
"""

import logging
from datetime import date, datetime, timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import DailyLog, DutyStatusRecord, LogSheet
from .serializers import (
    DailyLogSerializer,
    DailyLogCreateSerializer,
    DutyStatusRecordSerializer,
    LogSheetSerializer,
    ELDLogsGenerationRequestSerializer,
    ELDLogsGenerationResponseSerializer,
    LogCertificationSerializer,
    DutyStatusUpdateRequestSerializer,
    ELDComplianceReportSerializer,
    LogSheetGridSerializer,
    BulkLogOperationSerializer,
    BulkLogOperationResponseSerializer,
)
from .services.daily_log_generator import DailyLogGeneratorService
from .services.duty_status_tracker import DutyStatusTrackerService
from .services.log_sheet_renderer import LogSheetRendererService
from routes.models import Trip

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class DailyLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Daily Logs operations.
    
    Provides CRUD operations for daily logs including creation,
    updates, certification, and compliance validation.
    """
    
    queryset = DailyLog.objects.select_related('trip').prefetch_related('duty_status_records').all()
    serializer_class = DailyLogSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(log_date__gte=start_date_obj)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(log_date__lte=end_date_obj)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        # Filter by certification status
        is_certified = self.request.query_params.get('is_certified')
        if is_certified is not None:
            is_certified_bool = is_certified.lower() == 'true'
            queryset = queryset.filter(is_certified=is_certified_bool)
        
        return queryset.order_by('-log_date')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DailyLogCreateSerializer
        return super().get_serializer_class()
    
    def create(self, request, *args, **kwargs):
        """Create new daily log with validation."""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            trip_id = validated_data.pop('trip_id')
            
            # Get trip
            trip = get_object_or_404(Trip, id=trip_id)
            
            # Check if log already exists for this date
            existing_log = DailyLog.objects.filter(
                trip_id=trip_id,
                log_date=validated_data['log_date']
            ).first()
            
            if existing_log:
                return Response(
                    {'error': 'Daily log already exists for this date'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create daily log
            daily_log = DailyLog.objects.create(
                trip=trip,
                **validated_data
            )
            
            response_serializer = DailyLogSerializer(daily_log)
            
            logger.info(f"Created daily log {daily_log.id} for trip {trip_id}")
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating daily log: {str(e)}")
            return Response(
                {'error': 'Failed to create daily log', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def by_trip(self, request):
        """Get all daily logs for a specific trip."""
        logger.info(f"by_trip called with query_params: {request.query_params}")
        trip_id = request.query_params.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.get_queryset().filter(trip_id=trip_id)
        logger.info(f"Found {logs.count()} logs for trip_id: {trip_id}")
        serializer = self.get_serializer(logs, many=True)
        
        return Response({
            'trip_id': trip_id,
            'daily_logs': serializer.data,
            'total_logs': logs.count(),
            'certified_logs': logs.filter(is_certified=True).count(),
            'incomplete_logs': [log.id for log in logs if not log.is_complete]
        })
    
    @action(detail=True, methods=['post'])
    def certify(self, request, pk=None):
        """Certify a daily log with driver signature."""
        serializer = LogCertificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            daily_log = self.get_object()
            validated_data = serializer.validated_data
            
            # Verify driver name matches
            if daily_log.driver_name != validated_data['driver_name']:
                return Response(
                    {'error': 'Driver name does not match log'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Certify the log
            daily_log.certify_log()
            
            response_serializer = self.get_serializer(daily_log)
            
            logger.info(f"Certified daily log {pk}")
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Error certifying daily log {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to certify daily log'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def recalculate_totals(self, request, pk=None):
        """Recalculate total hours from duty status records."""
        try:
            daily_log = self.get_object()
            daily_log.calculate_totals()
            
            serializer = self.get_serializer(daily_log)
            
            logger.info(f"Recalculated totals for daily log {pk}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error recalculating totals for daily log {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to recalculate totals'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def validate_compliance(self, request, pk=None):
        """Validate daily log against HOS regulations."""
        try:
            daily_log = self.get_object()
            violations = daily_log.validate_compliance()
            
            return Response({
                'daily_log_id': str(pk),
                'violations': violations,
                'is_compliant': len(violations) == 0,
                'validated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error validating compliance for daily log {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to validate compliance'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ELDLogsGenerationViewSet(viewsets.ViewSet):
    """
    ViewSet for ELD logs generation.
    
    Provides endpoints for generating daily logs and log sheets
    for trips with automated ELD compliance.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate ELD logs for a trip.
        
        Request Body:
            trip_id (UUID): Trip identifier
            start_date (date): Start date for generation
            end_date (date, optional): End date for generation
            include_log_sheets (bool): Whether to generate visual log sheets
            sheet_format (string): Format for log sheets ('pdf' or 'json')
        """
        serializer = ELDLogsGenerationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            trip_id = validated_data['trip_id']
            
            # Get trip
            trip = get_object_or_404(Trip, id=trip_id)
            
            # Initialize generator service
            generator = DailyLogGeneratorService()
            
            # Generate logs
            result = generator.generate_logs_for_trip(
                trip=trip,
                start_date=validated_data['start_date'],
                end_date=validated_data['end_date'],
                include_log_sheets=validated_data['include_log_sheets'],
                sheet_format=validated_data['sheet_format']
            )
            
            # Prepare response
            generated_logs = DailyLog.objects.filter(
                trip_id=trip_id,
                log_date__range=[validated_data['start_date'], validated_data['end_date']]
            )
            
            log_sheets = []
            if validated_data['include_log_sheets']:
                log_sheets = LogSheet.objects.filter(
                    daily_log__in=generated_logs
                )
            
            response_data = {
                'trip_id': str(trip_id),
                'generated_logs': DailyLogSerializer(generated_logs, many=True).data,
                'generated_log_sheets': LogSheetSerializer(log_sheets, many=True).data,
                'generation_summary': {
                    'total_logs_generated': generated_logs.count(),
                    'total_sheets_generated': log_sheets.count(),
                    'date_range': f"{validated_data['start_date']} to {validated_data['end_date']}",
                    'sheet_format': validated_data['sheet_format']
                },
                'errors': result.get('errors', []),
                'warnings': result.get('warnings', []),
                'generated_at': timezone.now()
            }
            
            response_serializer = ELDLogsGenerationResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            logger.info(f"Generated ELD logs for trip {trip_id}")
            return Response(response_serializer.validated_data)
            
        except Exception as e:
            logger.error(f"ELD logs generation failed: {str(e)}")
            return Response(
                {'error': 'ELD logs generation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DutyStatusRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Duty Status Records operations.
    
    Provides CRUD operations for individual duty status change
    records within daily logs.
    """
    
    queryset = DutyStatusRecord.objects.select_related('daily_log').all()
    serializer_class = DutyStatusRecordSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by daily log ID
        daily_log_id = self.request.query_params.get('daily_log_id')
        if daily_log_id:
            queryset = queryset.filter(daily_log_id=daily_log_id)
        
        # Filter by duty status
        duty_status = self.request.query_params.get('duty_status')
        if duty_status:
            queryset = queryset.filter(duty_status=duty_status)
        
        return queryset.order_by('sequence_number')
    
    @action(detail=False, methods=['post'])
    def create_status_change(self, request):
        """
        Create a new duty status change record.
        
        Request Body:
            daily_log_id (UUID): Daily log to update
            new_duty_status (string): New duty status
            change_time (datetime): Time of status change
            location (string): Location of change
            odometer_reading (int, optional): Current odometer
            engine_hours (decimal, optional): Current engine hours
            remarks (string, optional): Additional remarks
        """
        serializer = DutyStatusUpdateRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            daily_log_id = validated_data['daily_log_id']
            
            # Get daily log
            daily_log = get_object_or_404(DailyLog, id=daily_log_id)
            
            # Use duty status tracker service
            tracker = DutyStatusTrackerService()
            
            duty_record = tracker.create_duty_status_record(
                daily_log=daily_log,
                duty_status=validated_data['new_duty_status'],
                change_time=validated_data['change_time'],
                location=validated_data['location'],
                odometer_reading=validated_data.get('odometer_reading'),
                engine_hours=validated_data.get('engine_hours'),
                remarks=validated_data.get('remarks', '')
            )
            
            # Recalculate daily log totals
            daily_log.calculate_totals()
            
            response_serializer = DutyStatusRecordSerializer(duty_record)
            
            logger.info(f"Created duty status record for daily log {daily_log_id}")
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating duty status record: {str(e)}")
            return Response(
                {'error': 'Failed to create duty status record', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Log Sheets operations.
    
    Provides operations for generating and retrieving visual
    log sheets in FMCSA-compliant format.
    """
    
    queryset = LogSheet.objects.select_related('daily_log').all()
    serializer_class = LogSheetSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by daily log ID
        daily_log_id = self.request.query_params.get('daily_log_id')
        if daily_log_id:
            queryset = queryset.filter(daily_log_id=daily_log_id)
        
        # Filter by sheet format
        sheet_format = self.request.query_params.get('sheet_format')
        if sheet_format:
            queryset = queryset.filter(sheet_format=sheet_format)
        
        return queryset.order_by('-generated_at')
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate log sheet for a daily log.
        
        Request Body:
            daily_log_id (UUID): Daily log to generate sheet for
            sheet_format (string): Format ('pdf' or 'json')
        """
        daily_log_id = request.data.get('daily_log_id')
        sheet_format = request.data.get('sheet_format', 'pdf')
        
        if not daily_log_id:
            return Response(
                {'error': 'daily_log_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get daily log
            daily_log = get_object_or_404(DailyLog, id=daily_log_id)
            
            # Use log sheet renderer service
            renderer = LogSheetRendererService()
            
            log_sheet = renderer.generate_log_sheet(
                daily_log=daily_log,
                sheet_format=sheet_format
            )
            
            serializer = self.get_serializer(log_sheet)
            
            logger.info(f"Generated log sheet for daily log {daily_log_id}")
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error generating log sheet: {str(e)}")
            return Response(
                {'error': 'Failed to generate log sheet', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def grid_data(self, request, pk=None):
        """Get grid data for visual representation."""
        try:
            log_sheet = self.get_object()
            
            if not log_sheet.grid_data:
                return Response(
                    {'error': 'Grid data not available for this log sheet'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(log_sheet.grid_data)
            
        except Exception as e:
            logger.error(f"Error retrieving grid data: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve grid data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ELDComplianceReportViewSet(viewsets.ViewSet):
    """
    ViewSet for ELD compliance reporting.
    
    Provides comprehensive compliance reports including
    log completeness, violations, and metrics.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def trip_report(self, request):
        """
        Generate comprehensive ELD compliance report for a trip.
        
        Query Parameters:
            trip_id (UUID): Trip identifier
            start_date (date, optional): Report start date
            end_date (date, optional): Report end date
        """
        trip_id = request.query_params.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get trip
            trip = get_object_or_404(Trip, id=trip_id)
            
            # Date range for report
            end_date = date.today()
            start_date = end_date - timedelta(days=30)  # Default to last 30 days
            
            # Override with query parameters if provided
            if request.query_params.get('start_date'):
                start_date = datetime.strptime(
                    request.query_params['start_date'], '%Y-%m-%d'
                ).date()
            
            if request.query_params.get('end_date'):
                end_date = datetime.strptime(
                    request.query_params['end_date'], '%Y-%m-%d'
                ).date()
            
            # Get daily logs in date range
            daily_logs = DailyLog.objects.filter(
                trip_id=trip_id,
                log_date__range=[start_date, end_date]
            ).order_by('log_date')
            
            # Calculate compliance metrics
            total_logs = daily_logs.count()
            certified_logs = daily_logs.filter(is_certified=True).count()
            incomplete_logs = sum(1 for log in daily_logs if not log.is_complete)
            
            # Gather violations
            violations = []
            for log in daily_logs:
                log_violations = log.validate_compliance()
                for violation in log_violations:
                    violation['daily_log_id'] = str(log.id)
                    violation['log_date'] = log.log_date.isoformat()
                violations.extend(log_violations)
            
            # Generate recommendations
            recommendations = []
            if incomplete_logs > 0:
                recommendations.append(f"{incomplete_logs} logs have incomplete hours (not totaling 24)")
            if certified_logs < total_logs:
                uncertified = total_logs - certified_logs
                recommendations.append(f"{uncertified} logs need driver certification")
            if violations:
                recommendations.append(f"{len(violations)} compliance violations need attention")
            
            # Compliance summary
            compliance_summary = {
                'total_logs': total_logs,
                'certified_logs': certified_logs,
                'incomplete_logs': incomplete_logs,
                'violation_count': len(violations),
                'compliance_percentage': (certified_logs / total_logs * 100) if total_logs > 0 else 0
            }
            
            report_data = {
                'trip_id': str(trip_id),
                'driver_name': trip.driver_name,
                'report_period_start': start_date,
                'report_period_end': end_date,
                'daily_logs': DailyLogSerializer(daily_logs, many=True).data,
                'total_logs': total_logs,
                'certified_logs': certified_logs,
                'incomplete_logs': incomplete_logs,
                'compliance_summary': compliance_summary,
                'violations': violations,
                'recommendations': recommendations,
                'report_generated_at': timezone.now()
            }
            
            serializer = ELDComplianceReportSerializer(data=report_data)
            serializer.is_valid(raise_exception=True)
            
            logger.info(f"Generated ELD compliance report for trip {trip_id}")
            return Response(serializer.validated_data)
            
        except Exception as e:
            logger.error(f"Error generating ELD compliance report: {str(e)}")
            return Response(
                {'error': 'Failed to generate compliance report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkLogOperationViewSet(viewsets.ViewSet):
    """
    ViewSet for bulk log operations.
    
    Provides endpoints for performing operations on
    multiple logs simultaneously.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def execute(self, request):
        """
        Execute bulk operation on multiple logs.
        
        Request Body:
            trip_id (UUID): Trip identifier
            operation (string): Operation type ('certify', 'generate', 'recalculate', 'validate')
            date_range (dict, optional): Date range for operation
            log_ids (list, optional): Specific log IDs
            parameters (dict, optional): Additional parameters
        """
        serializer = BulkLogOperationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            trip_id = validated_data['trip_id']
            operation = validated_data['operation']
            
            # Get logs to process
            if validated_data.get('log_ids'):
                logs = DailyLog.objects.filter(
                    id__in=validated_data['log_ids'],
                    trip_id=trip_id
                )
            elif validated_data.get('date_range'):
                date_range = validated_data['date_range']
                logs = DailyLog.objects.filter(
                    trip_id=trip_id,
                    log_date__range=[date_range['start_date'], date_range['end_date']]
                )
            else:
                logs = DailyLog.objects.filter(trip_id=trip_id)
            
            # Execute operation
            results = []
            errors = []
            successful = 0
            
            for log in logs:
                try:
                    if operation == 'certify':
                        log.certify_log()
                        results.append({
                            'log_id': str(log.id),
                            'status': 'certified',
                            'log_date': log.log_date.isoformat()
                        })
                    
                    elif operation == 'recalculate':
                        log.calculate_totals()
                        results.append({
                            'log_id': str(log.id),
                            'status': 'recalculated',
                            'totals': log.get_duty_status_summary()
                        })
                    
                    elif operation == 'validate':
                        violations = log.validate_compliance()
                        results.append({
                            'log_id': str(log.id),
                            'status': 'validated',
                            'violations': violations,
                            'is_compliant': len(violations) == 0
                        })
                    
                    successful += 1
                    
                except Exception as e:
                    errors.append({
                        'log_id': str(log.id),
                        'error': str(e)
                    })
            
            # Prepare response
            response_data = {
                'operation': operation,
                'total_logs_processed': logs.count(),
                'successful_operations': successful,
                'failed_operations': len(errors),
                'results': results,
                'errors': errors,
                'summary': {
                    'success_rate': (successful / logs.count() * 100) if logs.count() > 0 else 0,
                    'trip_id': str(trip_id)
                },
                'processed_at': timezone.now()
            }
            
            response_serializer = BulkLogOperationResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            
            logger.info(f"Executed bulk {operation} operation on {logs.count()} logs for trip {trip_id}")
            return Response(response_serializer.validated_data)
            
        except Exception as e:
            logger.error(f"Bulk operation failed: {str(e)}")
            return Response(
                {'error': 'Bulk operation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
