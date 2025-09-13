/**
 * Main Application Component - Phase 2 Implementation
 * 
 * Complete trucking logistics app with:
 * - Trip planning form
 * - Route map display
 * - ELD log sheet generation
 * - HOS compliance tracking
 */

import React, { useState } from 'react';
import { 
  AppLayout,
  TripPlanningForm, 
  RouteMap, 
  ELDLogSheet,
  HOSTracker
} from './components';
import './App.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('planning');

  // Mock driver information
  const driverInfo = {
    name: 'John Smith',
    cdlNumber: 'CDL-TX-123456789',
    coDriver: '',
    employeeId: 'EMP-001'
  };

  const handleTripSubmit = async (formData) => {
    setLoading(true);
    
    // Simulate API call to calculate route and generate logs
    try {
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const processedTripData = {
        ...formData,
        routeCalculated: true,
        estimatedDistance: 425,
        estimatedDuration: 7.5, // hours
        fuelStopsRequired: Math.ceil(425 / 300), // Every 300 miles
        restStopsRequired: formData.restBreakNeeded ? 1 : 0,
        complianceStatus: formData.currentCycleHours + 7.5 > 70 ? 'violation' : 
                         formData.currentCycleHours + 7.5 > 60 ? 'warning' : 'compliant'
      };
      
      setTripData(processedTripData);
      console.log('Trip data processed:', processedTripData);
      
    } catch (error) {
      console.error('Error processing trip:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentHours = tripData?.currentCycleHours || 28.5; // Default sample data
  const complianceStatus = tripData?.complianceStatus || (currentHours >= 70 ? 'violation' : currentHours >= 60 ? 'warning' : 'compliant');

  return (
    <AppLayout 
      currentHours={currentHours}
      complianceStatus={complianceStatus}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      {activeTab === 'planning' && (
        <div className="space-y-8">
          {/* Phase 2 Header */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-neutral-900">
              Trucking Logistics System
            </h2>
            <p className="text-neutral-600">
              Trip Planning, Route Mapping & ELD Log Generation
            </p>
          </div>

          {/* Main Interface - Two Column Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            {/* Left Column - Trip Planning */}
            <div className="space-y-6">
              <TripPlanningForm 
                onSubmit={handleTripSubmit}
                loading={loading}
              />
              
              {/* Quick Stats */}
              {tripData && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white p-4 rounded-lg border border-neutral-200">
                    <div className="text-sm text-neutral-600">Total Distance</div>
                    <div className="text-xl font-bold text-neutral-900">
                      {tripData.estimatedDistance} mi
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-neutral-200">
                    <div className="text-sm text-neutral-600">Est. Duration</div>
                    <div className="text-xl font-bold text-neutral-900">
                      {tripData.estimatedDuration.toFixed(1)} hrs
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column - Route Map */}
            <div>
              <RouteMap 
                tripData={tripData}
                className="h-full"
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
              DOT-compliant daily logs and duty status records
            </p>
          </div>

          {/* ELD Log Sheet */}
          <ELDLogSheet 
            tripData={tripData || {
              currentLocation: 'Terminal - Dallas, TX',
              pickupLocation: 'Warehouse - Houston, TX', 
              dropoffLocation: 'Distribution Center - Austin, TX',
              currentCycleHours: currentHours
            }}
            driverInfo={driverInfo}
          />
        </div>
      )}

      {activeTab === 'tracker' && (
        <div className="space-y-8">
          {/* HOS Tracker Header */}
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-neutral-900">
              Hours of Service Tracker
            </h2>
            <p className="text-neutral-600">
              Real-time HOS compliance monitoring and 8-day rolling totals
            </p>
          </div>

          {/* HOS Tracker */}
          <HOSTracker 
            currentHours={currentHours}
            tripData={tripData}
          />
        </div>
      )}
    </AppLayout>
  );
}

export default App;