/**
 * Trip Planning Form Component
 * 
 * Handles input for:
 * - Current location (with GPS functionality)
 * - Pickup location  
 * - Dropoff location
 * - Current Cycle Used (Hours)
 * 
 * Features LocationIQ autocomplete and GPS location detection.
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { MapPin, Truck, Clock, Navigation, Search } from 'lucide-react';
import { Button, Input, Card, CardHeader, CardTitle, CardContent, Loading, LocationAutocompleteInput } from '../common';
import { useCountryDetection } from '../../hooks';

const TripPlanningForm = ({ onSubmit, loading = false }) => {
  const [selectedLocations, setSelectedLocations] = useState({
    current: null,
    pickup: null,
    dropoff: null
  });

  // Country detection hook for dynamic location autocomplete (runs silently in background)
  const { 
    countryCode, 
    detectFromCoordinates 
  } = useCountryDetection({
    fallbackCountry: 'us'
    // Country detection happens silently - no callbacks or UI updates
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue
  } = useForm({
    defaultValues: {
      currentLocation: '',
      pickupLocation: '',
      dropoffLocation: '',
      currentCycleHours: 0,
      fuelLevel: 75,
      restBreakNeeded: false
    }
  });

  const watchedHours = watch('currentCycleHours');

  // Handle location selection from autocomplete
  const handleLocationSelect = (field) => (location) => {
    setSelectedLocations(prev => ({ ...prev, [field]: location }));
    setValue(field === 'current' ? 'currentLocation' : 
             field === 'pickup' ? 'pickupLocation' : 'dropoffLocation',
             location.displayName);
  };

  // Handle GPS location detection for current location
  // Per requirements: don't reverse geocode, just send coordinates to backend
  const handleGpsLocation = async (gpsData) => {
    // Try to detect country from GPS coordinates to update autocomplete (silently)
    try {
      await detectFromCoordinates(gpsData.lat, gpsData.lon);
    } catch (error) {
      console.warn('Could not detect country from GPS coordinates:', error);
    }

    // Create location object with GPS coordinates (no reverse geocoding)
    const syntheticLocation = {
      id: `gps_${Date.now()}`,
      displayName: `Current GPS Location`,
      address: {
        formatted: `GPS: ${gpsData.lat.toFixed(4)}, ${gpsData.lon.toFixed(4)}`,
        street: '',
        city: 'GPS Location',
        state: '',
        postalCode: '',
        country: '',
        countryCode: countryCode, // Use detected country code
      },
      coordinates: {
        lat: gpsData.lat,
        lon: gpsData.lon,
      },
      type: 'gps',
      category: 'gps',
      truckAccessible: true, // Assume GPS location is accessible
      importance: 1,
      accuracy: gpsData.accuracy,
      timestamp: gpsData.timestamp || Date.now(),
      // Additional GPS metadata that backend can use
      gpsData: {
        accuracy: gpsData.accuracy,
        altitude: gpsData.altitude,
        altitudeAccuracy: gpsData.altitudeAccuracy,
        heading: gpsData.heading,
        speed: gpsData.speed,
        timestamp: gpsData.timestamp
      }
    };
    
    setSelectedLocations(prev => ({ ...prev, current: syntheticLocation }));
    setValue('currentLocation', syntheticLocation.displayName);
  };

  const handleFormSubmit = (data) => {
    // Add validation for HOS compliance
    const formattedData = {
      ...data,
      currentCycleHours: parseFloat(data.currentCycleHours),
      fuelLevel: parseInt(data.fuelLevel),
      timestamp: new Date().toISOString(),
      locations: selectedLocations, // Include selected location objects
      complianceCheck: {
        withinLimits: data.currentCycleHours < 70,
        hoursRemaining: Math.max(0, 70 - data.currentCycleHours),
        canDrive: data.currentCycleHours < 60
      }
    };

    onSubmit(formattedData);
  };

  const getHoursStatusColor = () => {
    if (watchedHours >= 70) return 'text-error-600';
    if (watchedHours >= 60) return 'text-warning-600';
    return 'text-success-600';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-8 h-8 bg-primary-100 rounded-lg">
            <Navigation className="w-4 h-4 text-primary-600" />
          </div>
          <CardTitle>Trip Planning</CardTitle>
        </div>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
          {/* Hours of Service Status */}
          <div className="bg-neutral-50 p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Clock className="w-5 h-5 text-neutral-500" />
                <div>
                  <h4 className="font-medium text-neutral-900">Hours of Service Status</h4>
                  <p className="text-sm text-neutral-600">
                    Current cycle: <span className={`font-mono font-semibold ${getHoursStatusColor()}`}>
                      {watchedHours}/70 hours
                    </span>
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-sm font-medium ${getHoursStatusColor()}`}>
                  {watchedHours >= 70 ? 'VIOLATION' : watchedHours >= 60 ? 'WARNING' : 'COMPLIANT'}
                </div>
                <div className="text-xs text-neutral-500">
                  {Math.max(0, 70 - watchedHours)} hrs remaining
                </div>
              </div>
            </div>
          </div>

          {/* Current Cycle Hours Input */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Current Cycle Hours Used
            </label>
            <Input
              type="number"
              step="0.1"
              min="0"
              max="80"
              placeholder="0.0"
              {...register('currentCycleHours', {
                required: 'Current cycle hours is required',
                min: { value: 0, message: 'Hours cannot be negative' },
                max: { value: 80, message: 'Hours exceed maximum possible' }
              })}
              error={errors.currentCycleHours?.message}
              helperText="Total on-duty hours in current 8-day period"
            />
          </div>

          {/* Location Inputs with Autocomplete */}
          <div className="grid grid-cols-1 md:grid-cols-1 gap-6">
            {/* Current Location with GPS */}
            <LocationAutocompleteInput
              label="Current Location"
              placeholder="Enter current location or use GPS"
              value={watch('currentLocation')}
              onChange={(e) => setValue('currentLocation', e.target.value)}
              onLocationSelect={handleLocationSelect('current')}
              onGpsLocation={handleGpsLocation}
              {...register('currentLocation', {
                required: 'Current location is required'
              })}
              error={errors.currentLocation?.message}
              helperText="Your current position (GPS available)"
              icon={MapPin}
              showGpsButton={true}
              truckFriendly={true}
              countryCode={countryCode} // Dynamic country code (detected silently)
            />

            {/* Pickup Location */}
            <LocationAutocompleteInput
              label="Pickup Location"
              placeholder="Enter pickup address or facility"
              value={watch('pickupLocation')}
              onChange={(e) => setValue('pickupLocation', e.target.value)}
              onLocationSelect={handleLocationSelect('pickup')}
              {...register('pickupLocation', {
                required: 'Pickup location is required'
              })}
              error={errors.pickupLocation?.message}
              helperText="Where you'll pick up the load"
              icon={Truck}
              showGpsButton={false}
              truckFriendly={true}
              countryCode={countryCode} // Dynamic country code (detected silently)
            />

            {/* Dropoff Location */}
            <LocationAutocompleteInput
              label="Dropoff Location"
              placeholder="Enter delivery address"
              value={watch('dropoffLocation')}
              onChange={(e) => setValue('dropoffLocation', e.target.value)}
              onLocationSelect={handleLocationSelect('dropoff')}
              {...register('dropoffLocation', {
                required: 'Dropoff location is required'
              })}
              error={errors.dropoffLocation?.message}
              helperText="Final delivery destination"
              icon={MapPin}
              showGpsButton={false}
              truckFriendly={true}
              countryCode={countryCode} // Dynamic country code (detected silently)
            />
          </div>

          {/* Selected Locations Preview */}
          {Object.values(selectedLocations).some(loc => loc) && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-3 flex items-center">
                <MapPin className="w-4 h-4 mr-2" />
                Selected Locations
              </h4>
              <div className="space-y-2 text-sm">
                {selectedLocations.current && (
                  <div className="flex items-start space-x-2">
                    <span className="font-medium text-blue-800 min-w-[80px]">Current:</span>
                    <span className="text-blue-700">{selectedLocations.current.address.formatted}</span>
                    {selectedLocations.current.truckAccessible && (
                      <span className="text-green-600 text-xs flex items-center">
                        <Truck className="w-3 h-3 mr-1" />
                        Truck accessible
                      </span>
                    )}
                  </div>
                )}
                {selectedLocations.pickup && (
                  <div className="flex items-start space-x-2">
                    <span className="font-medium text-blue-800 min-w-[80px]">Pickup:</span>
                    <span className="text-blue-700">{selectedLocations.pickup.address.formatted}</span>
                    {selectedLocations.pickup.truckAccessible && (
                      <span className="text-green-600 text-xs flex items-center">
                        <Truck className="w-3 h-3 mr-1" />
                        Truck accessible
                      </span>
                    )}
                  </div>
                )}
                {selectedLocations.dropoff && (
                  <div className="flex items-start space-x-2">
                    <span className="font-medium text-blue-800 min-w-[80px]">Dropoff:</span>
                    <span className="text-blue-700">{selectedLocations.dropoff.address.formatted}</span>
                    {selectedLocations.dropoff.truckAccessible && (
                      <span className="text-green-600 text-xs flex items-center">
                        <Truck className="w-3 h-3 mr-1" />
                        Truck accessible
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Additional Trip Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Current Fuel Level (%)
              </label>
              <Input
                type="range"
                min="0"
                max="100"
                {...register('fuelLevel')}
                className="mb-2"
              />
              <div className="flex justify-between text-xs text-neutral-500">
                <span>0%</span>
                <span className="font-medium">{watch('fuelLevel')}%</span>
                <span>100%</span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="restBreakNeeded"
                {...register('restBreakNeeded')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-neutral-300 rounded"
              />
              <label htmlFor="restBreakNeeded" className="text-sm text-neutral-700">
                Schedule rest break during route
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex space-x-4">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="flex-1"
            >
              {loading ? 'Calculating Route...' : 'Plan Route & Generate ELD Log'}
            </Button>
          </div>

          {/* HOS Compliance Warning */}
          {watchedHours >= 60 && (
            <div className={`p-4 rounded-lg ${watchedHours >= 70 ? 'bg-error-50 text-error-800' : 'bg-warning-50 text-warning-800'}`}>
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-medium">
                    {watchedHours >= 70 ? 'HOS Violation' : 'HOS Warning'}
                  </h4>
                  <p className="text-sm mt-1">
                    {watchedHours >= 70 
                      ? 'You have exceeded the 70-hour limit. Further driving is prohibited until sufficient off-duty time is taken.'
                      : 'You are approaching the 70-hour limit. Plan for mandatory rest periods.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
};

export default TripPlanningForm;
