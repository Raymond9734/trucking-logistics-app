/**
 * Main Application Component - Phase 2 & 3 Implementation ✅
 * 
 * Complete trucking logistics app with REAL API integration:
 * - Trip planning form connected to Django backend
 * - Route map displaying actual route data
 * - ELD log sheet generation from backend
 * - HOS compliance tracking with real calculations
 */

import React, { useState } from 'react';
import {
AppLayout,
TripPlanningForm,
InteractiveMap, 
ELDLogSheet
} from './components';
import { apiService, apiUtils } from './services';
import './App.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('planning');

  // Driver information (could be fetched from API in production)
  const driverInfo = {
    name: 'John Smith',
    cdlNumber: 'CDL-TX-123456789',
    coDriver: '',
    employeeId: 'EMP-001'
  };

  /**
   * Handle trip form submission - Phase 2 Implementation
   * 
   * This function now makes REAL API calls to the Django backend:
   * 1. Validates trip data
   * 2. Calls the main trip calculation endpoint
   * 3. Fetches detailed route information
   * 4. Updates UI with real backend response
   */
  const handleTripSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🚀 Starting trip calculation with real API...');
      
      // Validate trip data before sending
      const validation = apiUtils.validateTripData(formData);
      if (!validation.isValid) {
        throw new Error(validation.errors.join(', '));
      }

      // Format data for backend API
      const tripPayload = apiUtils.formatTripDataForAPI(formData);
      console.log('📤 Sending trip data to backend:', tripPayload);
      
      // 🎯 MAIN API CALL - Trip Calculation
      const tripResponse = await apiService.routes.calculateTrip(tripPayload);
      console.log('✅ Trip calculation response:', tripResponse.data);
      
      // ✅ FIX: Backend returns trip_id, not id
      if (!tripResponse.data || (!tripResponse.data.id && !tripResponse.data.trip_id)) {
        throw new Error('Invalid response from trip calculation API');
      }
      
      // 🔍 Debug: Log response structure for development
      console.log('🔍 Response structure check:', {
        hasId: !!tripResponse.data.id,
        hasTripId: !!tripResponse.data.trip_id,
        hasRoute: !!tripResponse.data.route,
        hasCompliance: !!tripResponse.data.compliance,
        distance: tripResponse.data.route?.total_distance_miles,
        duration: tripResponse.data.route?.estimated_driving_time_hours || tripResponse.data.timeline?.total_timeline_hours
      });
      
      const calculatedTrip = tripResponse.data;
      // Use trip_id if id is not available
      const tripId = calculatedTrip.id || calculatedTrip.trip_id;
      
      // 🗺️ Fetch detailed route information (Phase 3)
      console.log('🗺️ Fetching route details for trip:', tripId);
      let detailedRoute = null;
      try {
        const routeResponse = await apiService.routes.getTripRoute(tripId);
        detailedRoute = routeResponse.data;
        console.log('✅ Route details fetched:', detailedRoute);
      } catch (routeError) {
        console.warn('⚠️ Could not fetch detailed route:', apiUtils.getErrorMessage(routeError));
        // Continue without detailed route data
      }
      
      // 📋 Fetch HOS status for the trip
      let hosStatus = null;
      try {
        const hosResponse = await apiService.hos.getStatusByTrip(tripId);
        hosStatus = hosResponse.data;
        console.log('✅ HOS status fetched:', hosStatus);
      } catch (hosError) {
        console.warn('⚠️ Could not fetch HOS status:', apiUtils.getErrorMessage(hosError));
      }
      
      // Process and format the response data for the frontend
      const processedTripData = {
        // Original form data
        ...formData,
        
        // Backend response data
        id: tripId, // Use the resolved trip ID (either id or trip_id)
        routeCalculated: true,
        
        // Distance and duration from backend (handle nested route data)
        estimatedDistance: calculatedTrip.total_distance_miles || 
                          calculatedTrip.route?.total_distance_miles || 
                          parseFloat(calculatedTrip.route?.total_distance_miles) || 0,
        estimatedDuration: calculatedTrip.estimated_duration_hours || 
                          calculatedTrip.route?.estimated_driving_time_hours || 
                          calculatedTrip.timeline?.total_timeline_hours || 0,
        
        // HOS compliance from backend (handle nested compliance data)
        complianceStatus: calculatedTrip.compliance_status || 
                         calculatedTrip.compliance?.is_compliant ? 'compliant' : 'unknown',
        currentCycleHours: parseFloat(formData.currentCycleHours || 0),
        
        // Route information
        routeGeometry: calculatedTrip.route_geometry,
        waypoints: calculatedTrip.waypoints || [],
        
        // Stops and breaks
        fuelStopsRequired: calculatedTrip.fuel_stops_required || 0,
        restStopsRequired: calculatedTrip.rest_stops_required || 0,
        mandatoryBreaks: calculatedTrip.mandatory_breaks || [],
        
        // HOS analysis
        hosAnalysis: calculatedTrip.hos_analysis || {},
        
        // Additional backend data
        backendData: calculatedTrip
      };
      
      // Update state with processed data
      setTripData(processedTripData);
      setRouteData(detailedRoute);
      
      console.log('✅ Trip processing completed successfully');
      console.log('📊 Final processed data:', processedTripData);
      
    } catch (error) {
      const errorMessage = apiUtils.getErrorMessage(error);
      console.error('❌ Trip calculation failed:', errorMessage);
      console.error('🔍 Full error:', error);
      
      setError(errorMessage);
      
      // Show user-friendly error message
      if (error.response?.status === 400) {
        setError('Please check your input data and try again.');
      } else if (error.response?.status >= 500) {
        setError('Server error occurred. Please try again later.');
      } else if (error.code === 'NETWORK_ERROR') {
        setError('Could not connect to server. Please check your internet connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Calculate current compliance status
  const getCurrentComplianceStatus = () => {
    if (!tripData) return 'unknown';
    
    const currentHours = tripData.currentCycleHours || 0;
    const estimatedHours = tripData.estimatedDuration || 0;
    const totalAfterTrip = currentHours + estimatedHours;
    
    if (totalAfterTrip >= 70) return 'violation';
    if (totalAfterTrip >= 60) return 'warning';
    return 'compliant';
  };

  const currentHours = tripData?.currentCycleHours || 0;
  const complianceStatus = tripData?.complianceStatus || getCurrentComplianceStatus();

  return (
    <AppLayout 
    currentHours={currentHours}
    complianceStatus={complianceStatus}
    activeTab={activeTab}
    onTabChange={setActiveTab}
    >
      {activeTab === 'planning' && (
        <div className="space-y-8">
          {/* Header */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-neutral-900">
              Trucking Logistics System
            </h2>
            <p className="text-neutral-600">
              Trip Planning, Route Mapping & ELD Log Generation
            </p>
            {loading && (
              <div className="flex items-center justify-center space-x-2 text-primary-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                <span className="text-sm">Processing with Django backend...</span>
              </div>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-error-50 border border-error-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-error-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-error-800 font-medium">Trip Calculation Error</h4>
                  <p className="text-error-700 text-sm mt-1">{error}</p>
                  <button 
                    onClick={() => setError(null)}
                    className="text-error-600 text-sm underline mt-2 hover:text-error-800"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Main Interface - Two Column Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            {/* Left Column - Trip Planning */}
            <div className="space-y-6">
              <TripPlanningForm 
                onSubmit={handleTripSubmit}
                loading={loading}
              />
              
              {/* Real Backend Stats */}
              {tripData && !loading && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white p-4 rounded-lg border border-neutral-200">
                    <div className="text-sm text-neutral-600">Total Distance</div>
                    <div className="text-xl font-bold text-neutral-900">
                      {tripData.estimatedDistance > 0 
                        ? `${Math.round(tripData.estimatedDistance)} mi`
                        : 'Calculating...'}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1">From backend calculation</div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-neutral-200">
                    <div className="text-sm text-neutral-600">Est. Duration</div>
                    <div className="text-xl font-bold text-neutral-900">
                      {tripData.estimatedDuration > 0 
                        ? `${tripData.estimatedDuration.toFixed(1)} hrs`
                        : 'Calculating...'}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1">Including mandatory breaks</div>
                  </div>
                </div>
              )}
              
              {/* Backend Response Debug (Development) */}
              {import.meta.env.VITE_DEBUG_MODE === 'true' && tripData && (
                <div className="bg-neutral-50 p-4 rounded-lg">
                  <h4 className="font-medium text-neutral-900 mb-2">Backend Response (Debug)</h4>
                  <details className="text-xs">
                    <summary className="cursor-pointer text-neutral-600">View raw backend data</summary>
                    <pre className="mt-2 text-neutral-700 overflow-auto">
                      {JSON.stringify(tripData.backendData, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </div>

            {/* Right Column - Interactive Route Map with Waypoints */}
            <div>
              <InteractiveMap 
                tripData={tripData}
                routeData={routeData}
                loading={loading}
                className=""
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="space-y-8">
          {/* ELD Logs Header */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-neutral-900">
              Electronic Logging Device (ELD) Records
            </h2>
            <p className="text-neutral-600">
              DOT-compliant daily logs generated from trip data
            </p>
          </div>

          {/* ELD Log Sheet with Real Trip Data */}
          <ELDLogSheet 
            tripData={tripData || {
              currentLocation: 'No trip calculated',
              pickupLocation: 'Enter trip details first', 
              dropoffLocation: 'Click "Plan Route" to generate logs',
              currentCycleHours: currentHours
            }}
            driverInfo={driverInfo}
          />
        </div>
      )}

      {activeTab === 'compliance' && (
        <div className="space-y-8">
          {/* Compliance Status Overview */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-neutral-900">
              HOS Compliance Status
            </h2>
            <p className="text-neutral-600">
              Current hours of service compliance summary
            </p>
          </div>

          {/* Simple Compliance Display */}
          <div className="max-w-2xl mx-auto">
            <div className="bg-white p-8 rounded-lg shadow-sm border border-neutral-200">
              <div className="text-center space-y-6">
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-neutral-900">Current Cycle Status</h3>
                  <div className={`text-4xl font-bold ${
                    currentHours >= 70 ? 'text-error-600' : 
                    currentHours >= 60 ? 'text-warning-600' : 
                    'text-success-600'
                  }`}>
                    {currentHours.toFixed(1)} / 70 hours
                  </div>
                  <p className="text-neutral-600">
                    Hours used in current 8-day cycle
                  </p>
                </div>
                
                <div className={`px-6 py-3 rounded-full text-lg font-medium ${
                  currentHours >= 70 ? 'bg-error-100 text-error-800' : 
                  currentHours >= 60 ? 'bg-warning-100 text-warning-800' : 
                  'bg-success-100 text-success-800'
                }`}>
                  {currentHours >= 70 ? 'VIOLATION - NO DRIVING PERMITTED' : 
                   currentHours >= 60 ? 'WARNING - APPROACHING LIMIT' : 
                   'COMPLIANT - SAFE TO DRIVE'}
                </div>
                
                <div className="text-sm text-neutral-600">
                  <p className="mb-2"><strong>Hours Remaining:</strong> {Math.max(0, 70 - currentHours).toFixed(1)} hours</p>
                  <p><strong>Daily Driving Limit:</strong> 11 hours after 10+ hours off duty</p>
                  <p><strong>Daily Duty Limit:</strong> 14-hour window for driving</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

export default App;