/**
 * Country Detection Debug Component
 * 
 * Simple debug utility to test and verify country detection functionality.
 * Can be temporarily added to any page for testing purposes.
 */

import React, { useState, useEffect } from 'react';
import { Globe, RefreshCw, MapPin, Wifi, Clock, Navigation2 } from 'lucide-react';

const CountryDetectionDebug = () => {
  const [status, setStatus] = useState('Initializing...');
  const [detectedCountry, setDetectedCountry] = useState(null);
  const [detectionMethod, setDetectionMethod] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // Dynamically import the service to avoid build issues if not ready
  useEffect(() => {
    const testCountryDetection = async () => {
      try {
        setStatus('Loading country detection service...');
        
        // Dynamic import to handle cases where service might not be ready
        const { countryDetection } = await import('../services/countryDetection');
        
        setStatus('Detecting country...');
        const country = await countryDetection.getCountryCode();
        const info = countryDetection.getDetectionInfo();
        
        setDetectedCountry(country);
        setDetectionMethod(info?.method);
        setStatus('Country detected successfully');
        setError(null);
      } catch (err) {
        console.error('Country detection test failed:', err);
        setError(err.message);
        setStatus('Detection failed');
        setDetectedCountry('us'); // Fallback
        setDetectionMethod('fallback');
      } finally {
        setLoading(false);
      }
    };

    testCountryDetection();
  }, []);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const { countryDetection } = await import('../services/countryDetection');
      const country = await countryDetection.refreshCountry();
      const info = countryDetection.getDetectionInfo();
      
      setDetectedCountry(country);
      setDetectionMethod(info?.method);
      setStatus('Country refreshed');
    } catch (err) {
      setError(err.message);
      setStatus('Refresh failed');
    } finally {
      setLoading(false);
    }
  };

  const getMethodIcon = (method) => {
    if (method?.includes('ip')) return <Wifi className="w-4 h-4" />;
    if (method?.includes('locale')) return <Globe className="w-4 h-4" />;
    if (method?.includes('timezone')) return <Clock className="w-4 h-4" />;
    if (method?.includes('gps')) return <Navigation2 className="w-4 h-4" />;
    return <MapPin className="w-4 h-4" />;
  };

  const getStatusColor = () => {
    if (error) return 'text-red-600 bg-red-50';
    if (loading) return 'text-blue-600 bg-blue-50';
    return 'text-green-600 bg-green-50';
  };

  const getCountryFlag = (countryCode) => {
    // Simple country code to flag emoji mapping
    const flags = {
      us: '🇺🇸', ke: '🇰🇪', gb: '🇬🇧', de: '🇩🇪', 
      fr: '🇫🇷', in: '🇮🇳', cn: '🇨🇳', au: '🇦🇺',
      ca: '🇨🇦', br: '🇧🇷', jp: '🇯🇵', za: '🇿🇦'
    };
    return flags[countryCode?.toLowerCase()] || '🌍';
  };

  if (!window.localStorage) {
    return (
      <div className="fixed bottom-4 right-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm">
        ⚠️ localStorage not available - country detection may not work properly
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 bg-white border border-neutral-200 rounded-lg shadow-lg p-4 max-w-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Globe className={`w-4 h-4 ${loading ? 'animate-spin' : 'text-blue-600'}`} />
          <span className="font-medium text-neutral-900">Country Detection</span>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="p-1 rounded-md hover:bg-neutral-100 disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Status */}
      <div className={`text-sm p-2 rounded-md mb-3 ${getStatusColor()}`}>
        {status}
      </div>

      {/* Detection Result */}
      {detectedCountry && (
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <span className="text-2xl">{getCountryFlag(detectedCountry)}</span>
            <div>
              <div className="font-medium text-neutral-900">
                {detectedCountry.toUpperCase()}
              </div>
              <div className="text-xs text-neutral-500">
                Country Code
              </div>
            </div>
          </div>

          {detectionMethod && (
            <div className="flex items-center space-x-2 text-sm text-neutral-600">
              {getMethodIcon(detectionMethod)}
              <span className="capitalize">
                {detectionMethod.replace(/_/g, ' ')}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-3 text-xs text-red-600 bg-red-50 p-2 rounded-md">
          {error}
        </div>
      )}

      {/* Debug Info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-3 pt-3 border-t border-neutral-200">
          <details className="text-xs text-neutral-500">
            <summary className="cursor-pointer hover:text-neutral-700">
              Debug Info
            </summary>
            <pre className="mt-2 whitespace-pre-wrap">
              {JSON.stringify({
                detectedCountry,
                detectionMethod,
                userAgent: navigator.userAgent.substring(0, 50) + '...',
                language: navigator.language,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                localStorage: !!window.localStorage,
                timestamp: new Date().toISOString()
              }, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

export default CountryDetectionDebug;
