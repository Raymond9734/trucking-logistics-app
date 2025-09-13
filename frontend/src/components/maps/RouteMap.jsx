/**
 * Route Map Component
 * 
 * Displays the planned route on OpenStreetMap with:
 * - Start, pickup, and dropoff locations
 * - Planned route path
 * - Rest stops and fuel stops
 * - HOS compliance information
 */

import React, { useState, useEffect } from 'react';
import { MapPin, Fuel, Coffee, Clock, Navigation } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Button } from '../common';

// Mock map component (since we can't load actual map libraries in this environment)
const RouteMap = ({ tripData, className = '' }) => {
  const [mapLoaded, setMapLoaded] = useState(false);
  const [routeCalculated, setRouteCalculated] = useState(false);

  // Mock route calculation
  useEffect(() => {
    if (tripData) {
      const timer = setTimeout(() => {
        setRouteCalculated(true);
        setMapLoaded(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [tripData]);

  // Mock route data
  const mockRouteInfo = {
    totalDistance: '425 miles',
    estimatedTime: '7 hours 30 minutes',
    fuelStops: 2,
    restStops: 1,
    hoursAfterTrip: tripData ? tripData.currentCycleHours + 7.5 : 0
  };

  if (!tripData) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-96 text-neutral-500">
          <div className="text-center">
            <MapPin className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
            <p>Enter trip details to view route</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Navigation className="w-5 h-5 text-primary-600" />
            <span>Route Map & Details</span>
          </CardTitle>
          <Button variant="secondary" size="sm">
            <Navigation className="w-4 h-4 mr-2" />
            Export Route
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Mock Map Display */}
        <div className="relative bg-neutral-100 rounded-lg h-96 overflow-hidden">
          {!mapLoaded ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
                <p className="text-neutral-600">Calculating route...</p>
              </div>
            </div>
          ) : (
            <div className="relative w-full h-full bg-gradient-to-br from-green-50 to-blue-50">
              {/* Mock Map Content */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center space-y-4">
                  {/* Route Path Visualization */}
                  <div className="relative">
                    <svg width="300" height="200" className="mx-auto">
                      {/* Background grid */}
                      <defs>
                        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" strokeWidth="0.5"/>
                        </pattern>
                      </defs>
                      <rect width="100%" height="100%" fill="url(#grid)" />
                      
                      {/* Route line */}
                      <path
                        d="M 50 150 Q 100 100 150 120 Q 200 140 250 80"
                        stroke="#3b82f6"
                        strokeWidth="4"
                        fill="none"
                        strokeDasharray="5,5"
                        className="animate-pulse"
                      />
                      
                      {/* Location markers */}
                      <circle cx="50" cy="150" r="8" fill="#22c55e" stroke="white" strokeWidth="2" />
                      <circle cx="150" cy="120" r="8" fill="#f59e0b" stroke="white" strokeWidth="2" />
                      <circle cx="250" cy="80" r="8" fill="#ef4444" stroke="white" strokeWidth="2" />
                      
                      {/* Rest/Fuel stops */}
                      <circle cx="120" cy="110" r="6" fill="#8b5cf6" stroke="white" strokeWidth="2" />
                      <circle cx="200" cy="130" r="6" fill="#06b6d4" stroke="white" strokeWidth="2" />
                    </svg>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div className="text-center">
                      <div className="w-4 h-4 bg-green-500 rounded-full mx-auto mb-1"></div>
                      <div className="font-medium">Current</div>
                      <div className="text-xs text-neutral-500 truncate">{tripData.currentLocation}</div>
                    </div>
                    <div className="text-center">
                      <div className="w-4 h-4 bg-yellow-500 rounded-full mx-auto mb-1"></div>
                      <div className="font-medium">Pickup</div>
                      <div className="text-xs text-neutral-500 truncate">{tripData.pickupLocation}</div>
                    </div>
                    <div className="text-center">
                      <div className="w-4 h-4 bg-red-500 rounded-full mx-auto mb-1"></div>
                      <div className="font-medium">Delivery</div>
                      <div className="text-xs text-neutral-500 truncate">{tripData.dropoffLocation}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Map Controls Overlay */}
              <div className="absolute top-4 right-4 space-y-2">
                <Button size="sm" variant="secondary" className="bg-white shadow-sm">
                  <MapPin className="w-4 h-4" />
                </Button>
                <Button size="sm" variant="secondary" className="bg-white shadow-sm">
                  +
                </Button>
                <Button size="sm" variant="secondary" className="bg-white shadow-sm">
                  −
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Route Information */}
        {routeCalculated && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <RouteInfoCard
              icon={Navigation}
              label="Distance"
              value={mockRouteInfo.totalDistance}
              color="text-blue-600"
            />
            <RouteInfoCard
              icon={Clock}
              label="Est. Time"
              value={mockRouteInfo.estimatedTime}
              color="text-green-600"
            />
            <RouteInfoCard
              icon={Fuel}
              label="Fuel Stops"
              value={`${mockRouteInfo.fuelStops} stops`}
              color="text-purple-600"
            />
            <RouteInfoCard
              icon={Coffee}
              label="Rest Stops"
              value={`${mockRouteInfo.restStops} break`}
              color="text-orange-600"
            />
          </div>
        )}

        {/* HOS Compliance Check */}
        {routeCalculated && (
          <div className={`p-4 rounded-lg ${
            mockRouteInfo.hoursAfterTrip > 70 
              ? 'bg-error-50 border border-error-200' 
              : mockRouteInfo.hoursAfterTrip > 60 
                ? 'bg-warning-50 border border-warning-200'
                : 'bg-success-50 border border-success-200'
          }`}>
            <div className="flex items-start space-x-3">
              <Clock className={`w-5 h-5 mt-0.5 ${
                mockRouteInfo.hoursAfterTrip > 70 
                  ? 'text-error-600' 
                  : mockRouteInfo.hoursAfterTrip > 60 
                    ? 'text-warning-600'
                    : 'text-success-600'
              }`} />
              <div className="flex-1">
                <h4 className={`font-medium ${
                  mockRouteInfo.hoursAfterTrip > 70 
                    ? 'text-error-800' 
                    : mockRouteInfo.hoursAfterTrip > 60 
                      ? 'text-warning-800'
                      : 'text-success-800'
                }`}>
                  HOS Compliance After Trip
                </h4>
                <p className={`text-sm mt-1 ${
                  mockRouteInfo.hoursAfterTrip > 70 
                    ? 'text-error-700' 
                    : mockRouteInfo.hoursAfterTrip > 60 
                      ? 'text-warning-700'
                      : 'text-success-700'
                }`}>
                  Total hours after trip completion: {mockRouteInfo.hoursAfterTrip.toFixed(1)}/70
                  {mockRouteInfo.hoursAfterTrip > 70 
                    ? ' - VIOLATION: Trip exceeds HOS limits'
                    : mockRouteInfo.hoursAfterTrip > 60
                      ? ' - WARNING: Approaching HOS limits'
                      : ' - COMPLIANT: Within HOS limits'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Planned Stops */}
        {routeCalculated && (
          <div>
            <h4 className="font-medium text-neutral-900 mb-3">Planned Stops</h4>
            <div className="space-y-2">
              <StopItem
                icon={Fuel}
                location="Flying J Travel Center - Mile 180"
                time="2 hours 30 min"
                type="Fuel Stop"
                details="Estimated fuel needed: 120 gallons"
              />
              <StopItem
                icon={Coffee}
                location="Rest Area - Mile 320"
                time="5 hours 45 min"
                type="Mandatory Rest Break"
                details="30-minute break required by HOS regulations"
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Route Info Card Component
const RouteInfoCard = ({ icon: Icon, label, value, color }) => (
  <div className="bg-white p-3 rounded-lg border border-neutral-200">
    <div className="flex items-center space-x-2">
      <Icon className={`w-4 h-4 ${color}`} />
      <span className="text-sm text-neutral-600">{label}</span>
    </div>
    <div className="text-lg font-semibold text-neutral-900 mt-1">{value}</div>
  </div>
);

// Stop Item Component
const StopItem = ({ icon: Icon, location, time, type, details }) => (
  <div className="flex items-start space-x-3 p-3 bg-neutral-50 rounded-lg">
    <Icon className="w-5 h-5 text-neutral-600 mt-0.5" />
    <div className="flex-1">
      <div className="flex items-center justify-between">
        <h5 className="font-medium text-neutral-900">{location}</h5>
        <span className="text-sm text-neutral-500">{time}</span>
      </div>
      <p className="text-sm text-primary-600 font-medium">{type}</p>
      <p className="text-xs text-neutral-500 mt-1">{details}</p>
    </div>
  </div>
);

export default RouteMap;