/**
 * Waypoint Details Component
 * 
 * Displays detailed information about route waypoints including:
 * - Stop type and duration
 * - HOS regulation references
 * - Distance and timing information
 * - Mandatory vs optional stops
 */

import React from 'react';
import { MapPin, Fuel, Coffee, Clock, AlertTriangle, CheckCircle, Truck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../common';

const WaypointDetails = ({ waypoints, className = '' }) => {
  if (!waypoints || waypoints.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="text-center py-8 text-neutral-500">
          <MapPin className="w-8 h-8 mx-auto mb-2 text-neutral-300" />
          <p>No waypoints to display</p>
        </CardContent>
      </Card>
    );
  }

  // Normalize waypoint data to handle different backend formats
  const normalizedWaypoints = waypoints.map((waypoint, index) => ({
    ...waypoint,
    // Ensure required fields have default values
    waypoint_type: waypoint.waypoint_type || waypoint.type || 'route_point',
    address: waypoint.address || waypoint.location || waypoint.name || `Waypoint ${index + 1}`,
    is_mandatory_stop: waypoint.is_mandatory_stop ?? waypoint.mandatory ?? false,
    estimated_stop_duration_minutes: parseInt(waypoint.estimated_stop_duration_minutes || waypoint.duration || 0),
    distance_from_previous_miles: parseFloat(waypoint.distance_from_previous_miles || waypoint.distance || 0),
    estimated_time_from_previous_minutes: parseInt(waypoint.estimated_time_from_previous_minutes || waypoint.time || 0),
    sequence_order: waypoint.sequence_order ?? waypoint.order ?? index,
    stop_reason: waypoint.stop_reason || waypoint.reason || '',
    hos_regulation: waypoint.hos_regulation || waypoint.regulation || ''
  }));

  const getWaypointIcon = (waypointType) => {
    const icons = {
      'origin': MapPin,
      'pickup': Truck,
      'dropoff': MapPin,
      'fuel_stop': Fuel,
      'break_30min': Coffee,
      'break_10hour': Coffee,
      'rest_stop': Coffee,
      'route_point': MapPin,
      'checkpoint': CheckCircle,
    };
    
    const IconComponent = icons[waypointType] || MapPin;
    return <IconComponent className="w-5 h-5" />;
  };

  const getWaypointColor = (waypointType, isMandatory) => {
    if (isMandatory) {
      const colors = {
        'pickup': 'text-blue-600 bg-blue-50 border-blue-200',
        'dropoff': 'text-red-600 bg-red-50 border-red-200',
        'fuel_stop': 'text-purple-600 bg-purple-50 border-purple-200',
        'break_30min': 'text-orange-600 bg-orange-50 border-orange-200',
        'break_10hour': 'text-indigo-600 bg-indigo-50 border-indigo-200',
        'rest_stop': 'text-green-600 bg-green-50 border-green-200',
      };
      return colors[waypointType] || 'text-neutral-600 bg-neutral-50 border-neutral-200';
    }
    return 'text-neutral-500 bg-neutral-50 border-neutral-200';
  };

  const getStopTypeName = (waypointType) => {
    const names = {
      'origin': 'Starting Location',
      'pickup': 'Pickup Location',
      'dropoff': 'Delivery Location',
      'fuel_stop': 'Fuel Stop',
      'break_30min': '30-Minute Break',
      'break_10hour': '10-Hour Rest',
      'rest_stop': 'Rest Stop',
      'route_point': 'Route Point',
      'checkpoint': 'Checkpoint',
    };
    return names[waypointType] || 'Unknown Stop';
  };

  const formatDuration = (minutes) => {
    if (minutes === 0) return 'No stop';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  };

  const cumulativeDistance = (waypoints, currentIndex) => {
    let total = 0;
    for (let i = 0; i <= currentIndex; i++) {
      total += parseFloat(waypoints[i].distance_from_previous_miles || 0);
    }
    return total;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <MapPin className="w-5 h-5 text-primary-600" />
          <span>Detailed Route Stops</span>
          <span className="text-sm font-normal text-neutral-500">
            ({normalizedWaypoints.length} waypoints)
          </span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-3">
        {normalizedWaypoints.map((waypoint, index) => {
          const totalDistance = cumulativeDistance(normalizedWaypoints, index);
          const colorClass = getWaypointColor(waypoint.waypoint_type, waypoint.is_mandatory_stop);
          
          return (
            <div
              key={waypoint.id || index}
              className={`p-4 rounded-lg border-2 ${colorClass} transition-colors hover:shadow-md`}
            >
              {/* Header Row */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 rounded-full bg-white shadow-sm border flex items-center justify-center">
                      {getWaypointIcon(waypoint.waypoint_type)}
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold text-neutral-900">
                      {getStopTypeName(waypoint.waypoint_type)}
                    </h4>
                    <p className="text-sm text-neutral-600 mt-1">
                      {waypoint.address || 'Location not specified'}
                    </p>
                  </div>
                </div>
                
                <div className="text-right text-sm">
                  <div className="font-medium text-neutral-900">
                    Mile {totalDistance.toFixed(0)}
                  </div>
                  {waypoint.is_mandatory_stop && (
                    <div className="text-xs text-red-600 font-medium mt-1">
                      MANDATORY
                    </div>
                  )}
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-neutral-600">Duration:</span>
                  <span className="font-medium text-neutral-900 ml-2">
                    {formatDuration(waypoint.estimated_stop_duration_minutes)}
                  </span>
                </div>
                
                <div>
                  <span className="text-neutral-600">Distance:</span>
                  <span className="font-medium text-neutral-900 ml-2">
                    {parseFloat(waypoint.distance_from_previous_miles || 0).toFixed(1)} mi
                  </span>
                </div>
                
                {waypoint.estimated_time_from_previous_minutes > 0 && (
                  <div>
                    <span className="text-neutral-600">Drive Time:</span>
                    <span className="font-medium text-neutral-900 ml-2">
                      {formatDuration(waypoint.estimated_time_from_previous_minutes)}
                    </span>
                  </div>
                )}
                
                <div>
                  <span className="text-neutral-600">Sequence:</span>
                  <span className="font-medium text-neutral-900 ml-2">
                    #{waypoint.sequence_order + 1}
                  </span>
                </div>
              </div>

              {/* Stop Reason */}
              {waypoint.stop_reason && (
                <div className="mt-3 p-3 bg-white/70 rounded border">
                  <h5 className="text-xs font-medium text-neutral-700 mb-1">Reason:</h5>
                  <p className="text-sm text-neutral-800">{waypoint.stop_reason}</p>
                </div>
              )}

              {/* HOS Regulation Reference */}
              {waypoint.hos_regulation && (
                <div className="mt-2 flex items-center space-x-2 text-xs">
                  <AlertTriangle className="w-3 h-3 text-amber-500" />
                  <span className="text-neutral-600">Regulation:</span>
                  <span className="font-mono font-medium text-neutral-800">
                    {waypoint.hos_regulation}
                  </span>
                </div>
              )}

              {/* Progress Indicator */}
              <div className="mt-3 w-full bg-neutral-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-blue-400 to-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${Math.min((totalDistance / (normalizedWaypoints[normalizedWaypoints.length - 1] ? 
                      cumulativeDistance(normalizedWaypoints, normalizedWaypoints.length - 1) : 1000)) * 100, 100)}%` 
                  }}
                />
              </div>
            </div>
          );
        })}
        
        {/* Summary Footer */}
        <div className="mt-6 p-4 bg-neutral-50 rounded-lg border">
          <h5 className="font-medium text-neutral-900 mb-2">Route Summary</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="text-center">
              <div className="text-xl font-bold text-blue-600">
                {normalizedWaypoints.filter(w => w.waypoint_type === 'fuel_stop').length}
              </div>
              <div className="text-neutral-600">Fuel Stops</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-orange-600">
                {normalizedWaypoints.filter(w => w.waypoint_type === 'break_30min').length}
              </div>
              <div className="text-neutral-600">30-Min Breaks</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-indigo-600">
                {normalizedWaypoints.filter(w => w.waypoint_type === 'break_10hour').length}
              </div>
              <div className="text-neutral-600">Rest Periods</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-neutral-600">
                {normalizedWaypoints.filter(w => w.is_mandatory_stop).length}
              </div>
              <div className="text-neutral-600">Mandatory</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default WaypointDetails;