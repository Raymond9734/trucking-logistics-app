"""
HOS Compliance API Views.

Provides REST API endpoints for HOS compliance tracking, calculations,
and violations management. Integrates with existing service layer
for business logic processing.
"""

import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import HOSStatus, RestBreak, ComplianceViolation
from .serializers import (
    HOSStatusSerializer,
    HOSCalculationRequestSerializer,
    HOSCalculationResponseSerializer,
    DutyStatusUpdateSerializer,
    RestBreakSerializer,
    ComplianceViolationSerializer,
    ComplianceViolationListSerializer,
    HOSComplianceReportSerializer,
    TripHOSPlanningSerializer,
    TripHOSPlanningResponseSerializer,
)
from .services.hos_calculator import HOSCalculatorService
from .services.compliance_validator import ComplianceValidatorService
from .services.rest_break_planner import RestBreakPlannerService
from routes.models import Trip

logger = logging.getLogger(__name__)


class HOSStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for HOS Status operations.
    
    Provides CRUD operations for HOS status tracking
    and real-time compliance monitoring.
    """
    
    queryset = HOSStatus.objects.select_related('trip').all()
    serializer_class = HOSStatusSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by trip ID
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)
        
        # Filter by compliance status
        can_drive = self.request.query_params.get('can_drive')
        if can_drive is not None:
            can_drive_bool = can_drive.lower() == 'true'
            queryset = queryset.filter(can_drive=can_drive_bool)
        
        return queryset.order_by('-calculated_at')
    
    @action(detail=False, methods=['get'])
    def by_trip(self, request):
        """
        Get HOS status for a specific trip.
        
        Query Parameters:
            trip_id (UUID): Trip identifier
        """
        trip_id = request.query_params.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            hos_status = get_object_or_404(HOSStatus, trip_id=trip_id)
            serializer = self.get_serializer(hos_status)
            
            logger.info(f"Retrieved HOS status for trip {trip_id}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error retrieving HOS status for trip {trip_id}: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve HOS status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, id=None):
        """
        Recalculate HOS status for updated data.
        
        Forces recalculation of available hours and compliance status.
        """
        try:
            hos_status = self.get_object()
            hos_status.calculate_available_hours()
            
            serializer = self.get_serializer(hos_status)
            
            logger.info(f"Recalculated HOS status {id}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error recalculating HOS status {id}: {str(e)}")
            return Response(
                {'error': 'Failed to recalculate HOS status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HOSCalculationViewSet(viewsets.ViewSet):
    """
    ViewSet for HOS calculations.
    
    Provides endpoints for calculating HOS compliance
    without persisting data to database.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate HOS compliance for given parameters.
        
        Request Body:
            current_cycle_hours (decimal): Current 8-day cycle hours
            current_duty_period_hours (decimal): Current duty period hours
            current_driving_hours (decimal): Current driving hours
            hours_since_last_break (decimal): Hours since last 30-min break
        """
        serializer = HOSCalculationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calculator = HOSCalculatorService()
            validated_data = serializer.validated_data
            
            result = calculator.calculate_available_hours(
                current_cycle_hours=validated_data['current_cycle_hours'],
                current_duty_period_hours=validated_data.get('current_duty_period_hours', Decimal('0')),
                current_driving_hours=validated_data.get('current_driving_hours', Decimal('0')),
                hours_since_last_break=validated_data.get('hours_since_last_break', Decimal('0'))
            )
            
            response_serializer = HOSCalculationResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=True)
            
            logger.info("HOS calculation completed successfully")
            return Response(response_serializer.validated_data)
            
        except Exception as e:
            logger.error(f"HOS calculation failed: {str(e)}")
            return Response(
                {'error': 'HOS calculation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def validate_compliance(self, request):
        """
        Validate HOS compliance for given parameters.
        
        Request Body: Same as calculate endpoint
        """
        serializer = HOSCalculationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calculator = HOSCalculatorService()
            validated_data = serializer.validated_data
            
            result = calculator.validate_hos_compliance(
                current_cycle_hours=validated_data['current_cycle_hours'],
                current_duty_period_hours=validated_data.get('current_duty_period_hours', Decimal('0')),
                current_driving_hours=validated_data.get('current_driving_hours', Decimal('0')),
                hours_since_last_break=validated_data.get('hours_since_last_break', Decimal('0'))
            )
            
            logger.info("HOS compliance validation completed")
            return Response(result)
            
        except Exception as e:
            logger.error(f"HOS compliance validation failed: {str(e)}")
            return Response(
                {'error': 'HOS compliance validation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def calculate_required_rest(self, request):
        """
        Calculate required rest time for compliance.
        
        Request Body: Same as calculate endpoint plus needs_30_minute_break
        """
        serializer = HOSCalculationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calculator = HOSCalculatorService()
            validated_data = serializer.validated_data
            
            needs_30_minute_break = request.data.get('needs_30_minute_break', False)
            
            result = calculator.calculate_required_rest(
                current_cycle_hours=validated_data['current_cycle_hours'],
                current_duty_period_hours=validated_data.get('current_duty_period_hours', Decimal('0')),
                current_driving_hours=validated_data.get('current_driving_hours', Decimal('0')),
                needs_30_minute_break=needs_30_minute_break
            )
            
            logger.info("Required rest calculation completed")
            return Response(result)
            
        except Exception as e:
            logger.error(f"Required rest calculation failed: {str(e)}")
            return Response(
                {'error': 'Required rest calculation failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def plan_trip(self, request):
        """
        Plan HOS compliance for an upcoming trip.
        
        Request Body:
            estimated_driving_hours (decimal): Expected driving time
            current_cycle_hours (decimal): Current 8-day cycle hours
            planned_start_time (datetime, optional): Trip start time
        """
        serializer = TripHOSPlanningSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            calculator = HOSCalculatorService()
            planner = RestBreakPlannerService()
            validated_data = serializer.validated_data
            
            # Calculate cycle impact
            cycle_analysis = calculator.calculate_cycle_hours_for_trip(
                estimated_driving_hours=validated_data['estimated_driving_hours'],
                current_cycle_hours=validated_data['current_cycle_hours']
            )
            
            # Plan required breaks
            break_plan = planner.plan_breaks_for_trip(
                estimated_driving_hours=validated_data['estimated_driving_hours'],
                planned_start_time=validated_data.get('planned_start_time', timezone.now())
            )
            
            # Combine results
            result = {
                'is_trip_feasible': not cycle_analysis['exceeds_cycle_limit'],
                'total_trip_time_estimate': cycle_analysis['estimated_trip_hours'],
                'required_breaks': break_plan.get('required_breaks', []),
                'recommended_start_time': validated_data.get('planned_start_time', timezone.now()),
                'cycle_impact': cycle_analysis,
                'warnings': [],
                'calculated_at': timezone.now()
            }
            
            if cycle_analysis['exceeds_cycle_limit']:
                result['warnings'].append('Trip exceeds 70-hour cycle limit - 34-hour restart required')
            
            response_serializer = TripHOSPlanningResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=True)
            
            logger.info("Trip HOS planning completed")
            return Response(response_serializer.validated_data)
            
        except Exception as e:
            logger.error(f"Trip HOS planning failed: {str(e)}")
            return Response(
                {'error': 'Trip HOS planning failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DutyStatusViewSet(viewsets.ViewSet):
    """
    ViewSet for duty status management.
    
    Handles updating driver duty status and recalculating
    HOS compliance based on status changes.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def update(self, request):
        """
        Update driver duty status and recalculate HOS.
        
        Request Body:
            trip_id (UUID): Trip identifier
            new_duty_status (string): New duty status
            location (string, optional): Location of status change
            remarks (string, optional): Additional remarks
        """
        serializer = DutyStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            trip_id = validated_data['trip_id']
            
            # Get HOS status for trip
            hos_status = get_object_or_404(HOSStatus, trip_id=trip_id)
            
            # Update duty status
            old_status = hos_status.current_duty_status
            hos_status.current_duty_status = validated_data['new_duty_status']
            hos_status.last_duty_status_change = timezone.now()
            
            # Recalculate HOS compliance
            hos_status.calculate_available_hours()
            
            # Create duty status change record in ELD logs if needed
            # (This would integrate with ELD logs app)
            
            result = {
                'trip_id': str(trip_id),
                'old_duty_status': old_status,
                'new_duty_status': hos_status.current_duty_status,
                'changed_at': hos_status.last_duty_status_change.isoformat(),
                'location': validated_data.get('location', ''),
                'remarks': validated_data.get('remarks', ''),
                'updated_hos_status': HOSStatusSerializer(hos_status).data
            }
            
            logger.info(f"Updated duty status for trip {trip_id}: {old_status} -> {hos_status.current_duty_status}")
            return Response(result)
            
        except HOSStatus.DoesNotExist:
            return Response(
                {'error': 'HOS status not found for trip'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating duty status: {str(e)}")
            return Response(
                {'error': 'Failed to update duty status', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ComplianceViolationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for compliance violations.
    
    Provides CRUD operations for HOS compliance violations
    and violation management.
    """
    
    queryset = ComplianceViolation.objects.select_related('trip').all()
    serializer_class = ComplianceViolationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter violations based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by trip ID
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by resolution status
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            is_resolved_bool = is_resolved.lower() == 'true'
            queryset = queryset.filter(is_resolved=is_resolved_bool)
        
        return queryset.order_by('-occurred_at')
    
    @action(detail=False, methods=['get'])
    def by_trip(self, request):
        """Get all violations for a specific trip."""
        trip_id = request.query_params.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        violations = self.get_queryset().filter(trip_id=trip_id)
        serializer = self.get_serializer(violations, many=True)
        
        return Response({
            'trip_id': trip_id,
            'violations': serializer.data,
            'total_violations': violations.count(),
            'unresolved_violations': violations.filter(is_resolved=False).count()
        })
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark a violation as resolved."""
        try:
            violation = self.get_object()
            resolution_notes = request.data.get('resolution_notes', '')
            
            violation.is_resolved = True
            violation.resolution_notes = resolution_notes
            violation.save()
            
            serializer = self.get_serializer(violation)
            
            logger.info(f"Resolved violation {pk}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error resolving violation {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to resolve violation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RestBreakViewSet(viewsets.ModelViewSet):
    """
    ViewSet for rest breaks.
    
    Provides CRUD operations for rest break tracking
    and break planning.
    """
    
    queryset = RestBreak.objects.select_related('trip').all()
    serializer_class = RestBreakSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter rest breaks based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by trip ID
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)
        
        # Filter by break type
        break_type = self.request.query_params.get('break_type')
        if break_type:
            queryset = queryset.filter(break_type=break_type)
        
        return queryset.order_by('-start_time')
    
    @action(detail=False, methods=['post'])
    def plan_breaks(self, request):
        """
        Plan required breaks for a trip.
        
        Request Body:
            estimated_driving_hours (decimal): Expected driving time
            planned_start_time (datetime): Trip start time
        """
        try:
            estimated_driving_hours = Decimal(str(request.data.get('estimated_driving_hours', 0)))
            planned_start_time = request.data.get('planned_start_time', timezone.now())
            
            if isinstance(planned_start_time, str):
                from datetime import datetime
                planned_start_time = datetime.fromisoformat(planned_start_time.replace('Z', '+00:00'))
            
            planner = RestBreakPlannerService()
            break_plan = planner.plan_breaks_for_trip(
                estimated_driving_hours=estimated_driving_hours,
                planned_start_time=planned_start_time
            )
            
            logger.info(f"Planned breaks for {estimated_driving_hours}h trip")
            return Response(break_plan)
            
        except Exception as e:
            logger.error(f"Break planning failed: {str(e)}")
            return Response(
                {'error': 'Break planning failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HOSComplianceReportViewSet(viewsets.ViewSet):
    """
    ViewSet for HOS compliance reports.
    
    Provides comprehensive reporting for HOS compliance
    status, violations, and recommendations.
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def trip_report(self, request):
        """
        Generate comprehensive HOS compliance report for a trip.
        
        Query Parameters:
            trip_id (UUID): Trip identifier
        """
        trip_id = request.query_params.get('trip_id')
        if not trip_id:
            return Response(
                {'error': 'trip_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get trip and HOS data
            trip = get_object_or_404(Trip, id=trip_id)
            hos_status = get_object_or_404(HOSStatus, trip_id=trip_id)
            violations = ComplianceViolation.objects.filter(trip_id=trip_id)
            rest_breaks = RestBreak.objects.filter(trip_id=trip_id)
            
            # Generate compliance recommendations
            validator = ComplianceValidatorService()
            recommendations = validator.get_compliance_recommendations(hos_status)
            
            # Calculate compliance score
            compliance_score = 100
            if violations.exists():
                unresolved_violations = violations.filter(is_resolved=False).count()
                compliance_score = max(0, 100 - (unresolved_violations * 20))
            
            report_data = {
                'trip_id': str(trip_id),
                'driver_name': trip.driver_name,
                'current_status': HOSStatusSerializer(hos_status).data,
                'violations': ComplianceViolationSerializer(violations, many=True).data,
                'rest_breaks': RestBreakSerializer(rest_breaks, many=True).data,
                'compliance_score': compliance_score,
                'recommendations': recommendations,
                'report_generated_at': timezone.now()
            }
            
            logger.info(f"Generated HOS compliance report for trip {trip_id}")
            return Response(report_data)
            
        except Exception as e:
            logger.error(f"Error generating compliance report for trip {trip_id}: {str(e)}")
            return Response(
                {'error': 'Failed to generate compliance report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
