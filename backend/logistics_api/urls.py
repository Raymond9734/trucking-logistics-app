"""
URL configuration for logistics_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    """API root endpoint with available endpoints."""
    return JsonResponse({
        'message': 'Trucking Logistics API',
        'version': '1.0',
        'endpoints': {
            'routes': '/api/routes/',
            'hos_compliance': '/api/hos/',
            'eld_logs': '/api/eld/',
            'admin': '/admin/',
        },
        'documentation': {
            'hos_compliance': {
                'description': 'Hours of Service compliance tracking and calculations',
                'endpoints': {
                    'status': 'GET /api/hos/status/ - List HOS statuses',
                    'status_by_trip': 'GET /api/hos/status/by-trip/?trip_id=<uuid> - Get status for trip',
                    'calculate': 'POST /api/hos/calculate/ - Calculate HOS compliance',
                    'validate': 'POST /api/hos/validate-compliance/ - Validate compliance',
                    'plan_trip': 'POST /api/hos/plan-trip/ - Plan trip compliance',
                    'violations': 'GET /api/hos/violations/ - List violations',
                    'reports': 'GET /api/hos/reports/trip/?trip_id=<uuid> - Generate reports',
                }
            },
            'eld_logs': {
                'description': 'Electronic Logging Device compliance and daily logs',
                'endpoints': {
                    'daily_logs': 'GET /api/eld/daily-logs/ - List daily logs',
                    'logs_by_trip': 'GET /api/eld/daily-logs/by-trip/?trip_id=<uuid> - Get logs for trip',
                    'generate_logs': 'POST /api/eld/generate/ - Generate ELD logs',
                    'certify_log': 'POST /api/eld/daily-logs/<uuid>/certify/ - Certify log',
                    'log_sheets': 'GET /api/eld/log-sheets/ - List log sheets',
                    'reports': 'GET /api/eld/reports/trip/?trip_id=<uuid> - Generate reports',
                }
            }
        }
    })

urlpatterns = [
    # Admin interface
    path("admin/", admin.site.urls),
    
    # API root
    path("api/", api_root, name='api-root'),
    
    # Routes API (existing)
    path("api/routes/", include("routes.urls")),
    
    # HOS Compliance API
    path("api/hos/", include("hos_compliance.urls")),
    
    # ELD Logs API
    path("api/eld/", include("eld_logs.urls")),
]
