"""
URL configuration for HOS Compliance API endpoints.

Provides URL routing for all HOS compliance related endpoints
including status tracking, calculations, violations, and reports.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HOSStatusViewSet,
    HOSCalculationViewSet,
    DutyStatusViewSet,
    ComplianceViolationViewSet,
    RestBreakViewSet,
    HOSComplianceReportViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'status', HOSStatusViewSet, basename='hos-status')
router.register(r'violations', ComplianceViolationViewSet, basename='hos-violations')
router.register(r'rest-breaks', RestBreakViewSet, basename='hos-rest-breaks')

# Custom URL patterns for non-model viewsets and specific actions
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # HOS Calculations endpoints
    path('calculate/', 
         HOSCalculationViewSet.as_view({'post': 'calculate'}), 
         name='hos-calculate'),
    path('validate-compliance/', 
         HOSCalculationViewSet.as_view({'post': 'validate_compliance'}), 
         name='hos-validate-compliance'),
    path('calculate-required-rest/', 
         HOSCalculationViewSet.as_view({'post': 'calculate_required_rest'}), 
         name='hos-calculate-required-rest'),
    path('plan-trip/', 
         HOSCalculationViewSet.as_view({'post': 'plan_trip'}), 
         name='hos-plan-trip'),
    
    # Duty Status endpoints
    path('duty-status/update/', 
         DutyStatusViewSet.as_view({'post': 'update'}), 
         name='hos-duty-status-update'),
    
    # Rest Break endpoints  
    path('rest-breaks/plan/', 
         RestBreakViewSet.as_view({'post': 'plan_breaks'}), 
         name='hos-plan-breaks'),
    
    # Compliance Reports endpoints
    path('reports/trip/', 
         HOSComplianceReportViewSet.as_view({'get': 'trip_report'}), 
         name='hos-trip-report'),
    
    # Specific status endpoints (alternative to router)
    path('status/by-trip/', 
         HOSStatusViewSet.as_view({'get': 'by_trip'}), 
         name='hos-status-by-trip'),
    path('status/<uuid:id>/recalculate/', 
         HOSStatusViewSet.as_view({'post': 'recalculate'}), 
         name='hos-status-recalculate'),
    
    # Specific violation endpoints
    path('violations/by-trip/', 
         ComplianceViolationViewSet.as_view({'get': 'by_trip'}), 
         name='hos-violations-by-trip'),
    path('violations/<uuid:pk>/resolve/', 
         ComplianceViolationViewSet.as_view({'post': 'resolve'}), 
         name='hos-violations-resolve'),
]

# URL patterns for API documentation purposes
hos_patterns = [
    # GET endpoints
    path('status/', 
         'List all HOS statuses with optional filtering'),
    path('status/<uuid:id>/', 
         'Retrieve specific HOS status'),
    path('status/by-trip/?trip_id=<uuid>', 
         'Get HOS status for specific trip'),
    
    path('violations/', 
         'List compliance violations with optional filtering'),
    path('violations/<uuid:id>/', 
         'Retrieve specific violation'),
    path('violations/by-trip/?trip_id=<uuid>', 
         'Get violations for specific trip'),
    
    path('rest-breaks/', 
         'List rest breaks with optional filtering'),
    path('rest-breaks/<uuid:id>/', 
         'Retrieve specific rest break'),
    
    path('reports/trip/?trip_id=<uuid>', 
         'Generate comprehensive compliance report for trip'),
    
    # POST endpoints
    path('calculate/', 
         'Calculate HOS compliance for given parameters'),
    path('validate-compliance/', 
         'Validate current HOS status against regulations'),
    path('calculate-required-rest/', 
         'Calculate required rest time for compliance'),
    path('plan-trip/', 
         'Plan HOS compliance for upcoming trip'),
    
    path('duty-status/update/', 
         'Update driver duty status and recalculate HOS'),
    path('rest-breaks/plan/', 
         'Plan required breaks for a trip'),
    
    path('status/<uuid:id>/recalculate/', 
         'Recalculate specific HOS status'),
    path('violations/<uuid:id>/resolve/', 
         'Mark violation as resolved'),
    
    # PUT/PATCH endpoints
    path('status/<uuid:id>/', 
         'Update specific HOS status'),
    path('violations/<uuid:id>/', 
         'Update specific violation'),
    path('rest-breaks/<uuid:id>/', 
         'Update specific rest break'),
    
    # DELETE endpoints
    path('violations/<uuid:id>/', 
         'Delete specific violation'),
    path('rest-breaks/<uuid:id>/', 
         'Delete specific rest break'),
]
