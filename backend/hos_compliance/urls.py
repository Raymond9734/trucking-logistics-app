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

# API Documentation - Available Endpoints:
"""
GET Endpoints:
- /api/hos/status/ - List all HOS statuses with optional filtering
- /api/hos/status/<uuid:id>/ - Retrieve specific HOS status  
- /api/hos/status/by-trip/?trip_id=<uuid> - Get HOS status for specific trip
- /api/hos/violations/ - List compliance violations with optional filtering
- /api/hos/violations/<uuid:id>/ - Retrieve specific violation
- /api/hos/violations/by-trip/?trip_id=<uuid> - Get violations for specific trip
- /api/hos/rest-breaks/ - List rest breaks with optional filtering
- /api/hos/rest-breaks/<uuid:id>/ - Retrieve specific rest break
- /api/hos/reports/trip/?trip_id=<uuid> - Generate comprehensive compliance report for trip

POST Endpoints:
- /api/hos/calculate/ - Calculate HOS compliance for given parameters
- /api/hos/validate-compliance/ - Validate current HOS status against regulations
- /api/hos/calculate-required-rest/ - Calculate required rest time for compliance
- /api/hos/plan-trip/ - Plan HOS compliance for upcoming trip
- /api/hos/duty-status/update/ - Update driver duty status and recalculate HOS
- /api/hos/rest-breaks/plan/ - Plan required breaks for a trip
- /api/hos/status/<uuid:id>/recalculate/ - Recalculate specific HOS status
- /api/hos/violations/<uuid:id>/resolve/ - Mark violation as resolved

PUT/PATCH Endpoints:
- /api/hos/status/<uuid:id>/ - Update specific HOS status
- /api/hos/violations/<uuid:id>/ - Update specific violation
- /api/hos/rest-breaks/<uuid:id>/ - Update specific rest break

DELETE Endpoints:
- /api/hos/violations/<uuid:id>/ - Delete specific violation
- /api/hos/rest-breaks/<uuid:id>/ - Delete specific rest break
"""
