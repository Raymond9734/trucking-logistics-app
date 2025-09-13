/**
 * Location Integration Test Component
 * 
 * Test component to verify dynamic country detection and GPS functionality
 * This can be used for development testing purposes.
 */

import React, { useState } from 'react';
import { MapPin, Globe, Navigation, RefreshCw } from 'lucide-react';
import { useCountryDetection, useGeoLocation } from '../hooks';
import { locationService } from '../services';
import { Button, Card, CardHeader, CardTitle, CardContent } from './common';

const LocationIntegrationTest = () => {
  const [testResults, setTestResults] = useState([]);
  
  const { 
    countryCode, 
    loading: countryLoading, 
    detectionInfo,
    refreshCountry,
    detectFromCoordinates 
  } = useCountryDetection({
    onCountryDetected: (country) => {
      addTestResult(`Country detected: ${country.toUpperCase()}`, 'success');
    },
    onCountryChanged: (country) => {
      addTestResult(`Country changed to: ${country.toUpperCase()}`, 'info');
    }
  });

  const { 
    getCurrentLocation, 
    loading: gpsLoading 
  } = useGeoLocation();

  const addTestResult = (message, type = 'info') => {
    const result = {
      id: Date.now(),
      message,
      type,
      timestamp: new Date().toLocaleTimeString()
    };
    setTestResults(prev => [result, ...prev].slice(0, 10)); // Keep last 10 results
  };

  const testLocationSearch = async () => {
    try {
      addTestResult('Testing location search...', 'info');
      const results = await locationService.autocomplete('truck stop', {
        countryCode,
        limit: 3,
        truckFriendly: true
      });
      addTestResult(`Found ${results.length} truck stops in ${countryCode.toUpperCase()}`, 'success');
    } catch (error) {
      addTestResult(`Location search failed: ${error.message}`, 'error');
    }
  };

  const testGPSLocation = async () => {
    try {
      addTestResult('Getting GPS location...', 'info');
      const location = await getCurrentLocation();
      addTestResult(
        `GPS: ${location.lat.toFixed(4)}, ${location.lon.toFixed(4)} (±${location.accuracy}m)`, 
        'success'
      );
      
      // Test country detection from coordinates
      const detectedCountry = await detectFromCoordinates(location.lat, location.lon);
      if (detectedCountry) {
        addTestResult(`GPS suggests country: ${detectedCountry.toUpperCase()}`, 'info');
      }
    } catch (error) {
      addTestResult(`GPS failed: ${error.message}`, 'error');
    }
  };

  const testRefreshCountry = async () => {
    try {
      addTestResult('Refreshing country detection...', 'info');
      const country = await refreshCountry();
      addTestResult(`Refreshed country: ${country.toUpperCase()}`, 'success');
    } catch (error) {
      addTestResult(`Refresh failed: ${error.message}`, 'error');
    }
  };

  const getResultColor = (type) => {
    switch (type) {
      case 'success': return 'text-green-600';
      case 'error': return 'text-red-600';
      case 'info': return 'text-blue-600';
      default: return 'text-neutral-600';
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <MapPin className="w-5 h-5" />
          <span>Location Integration Test</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Current Status */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex items-center space-x-2">
              <Globe className={`w-4 h-4 ${countryLoading ? 'animate-pulse' : ''} text-blue-600`} />
              <div>
                <div className="font-medium text-blue-900">Country Code</div>
                <div className="text-sm text-blue-700">
                  {countryLoading ? 'Detecting...' : countryCode.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="flex items-center space-x-2">
              <Navigation className="w-4 h-4 text-green-600" />
              <div>
                <div className="font-medium text-green-900">Detection Method</div>
                <div className="text-sm text-green-700 capitalize">
                  {detectionInfo?.method?.replace('_', ' ') || 'Unknown'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Test Buttons */}
        <div className="grid grid-cols-3 gap-3">
          <Button
            onClick={testLocationSearch}
            variant="outline"
            size="sm"
            disabled={countryLoading}
          >
            Test Search
          </Button>
          
          <Button
            onClick={testGPSLocation}
            variant="outline"
            size="sm"
            disabled={gpsLoading}
          >
            Test GPS
          </Button>
          
          <Button
            onClick={testRefreshCountry}
            variant="outline"
            size="sm"
            disabled={countryLoading}
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            Refresh
          </Button>
        </div>

        {/* Test Results */}
        <div>
          <h4 className="font-medium text-neutral-900 mb-3">Test Results</h4>
          <div className="bg-neutral-50 rounded-lg p-4 max-h-60 overflow-y-auto">
            {testResults.length === 0 ? (
              <p className="text-neutral-500 text-sm">No tests run yet</p>
            ) : (
              <div className="space-y-2">
                {testResults.map(result => (
                  <div key={result.id} className="flex justify-between items-start">
                    <span className={`text-sm ${getResultColor(result.type)}`}>
                      {result.message}
                    </span>
                    <span className="text-xs text-neutral-400 ml-2">
                      {result.timestamp}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Debug Info */}
        {detectionInfo && (
          <div className="bg-neutral-100 p-3 rounded-lg">
            <h5 className="text-xs font-medium text-neutral-600 mb-2">Debug Info</h5>
            <pre className="text-xs text-neutral-600 whitespace-pre-wrap">
              {JSON.stringify(detectionInfo, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default LocationIntegrationTest;
