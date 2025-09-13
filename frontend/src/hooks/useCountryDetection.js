/**
 * useCountryDetection Hook
 * 
 * React hook that integrates with the CountryDetectionService
 * to provide dynamic country code detection for location services.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { countryDetection } from '../services/countryDetection';

/**
 * Hook for managing country detection
 * @param {Object} options - Options for country detection
 * @returns {Object} - { countryCode, loading, error, refreshCountry, setManualCountry }
 */
export function useCountryDetection(options = {}) {
  const [countryCode, setCountryCode] = useState('us'); // Default fallback
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detectionInfo, setDetectionInfo] = useState(null);
  
  // Use refs to store callbacks to avoid infinite re-renders
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // Initialize country detection - run only once
  useEffect(() => {
    const detectCountry = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const detectedCountry = await countryDetection.getCountryCode();
        setCountryCode(detectedCountry);
        setDetectionInfo(countryDetection.getDetectionInfo());
        
        // Only log in development mode and not in infinite loop
        if (process.env.NODE_ENV === 'development') {
          console.log(`🌍 Country detected silently: ${detectedCountry.toUpperCase()}`);
        }
        
        if (optionsRef.current.onCountryDetected) {
          optionsRef.current.onCountryDetected(detectedCountry);
        }
      } catch (err) {
        console.warn('Country detection failed, using default:', err);
        setError(err.message);
        setCountryCode(optionsRef.current.fallbackCountry || 'us');
      } finally {
        setLoading(false);
      }
    };

    detectCountry();
  }, []); // Empty dependency array - run only once on mount

  // Listen for country changes - run only once
  useEffect(() => {
    const unsubscribe = countryDetection.onCountryChange((newCountry) => {
      setCountryCode(newCountry);
      setDetectionInfo(countryDetection.getDetectionInfo());
      
      if (optionsRef.current.onCountryChanged) {
        optionsRef.current.onCountryChanged(newCountry);
      }
    });

    return unsubscribe;
  }, []); // Empty dependency array - run only once on mount

  // Refresh country detection
  const refreshCountry = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const newCountry = await countryDetection.refreshCountry();
      setCountryCode(newCountry);
      setDetectionInfo(countryDetection.getDetectionInfo());
      return newCountry;
    } catch (err) {
      console.warn('Country refresh failed:', err);
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Manually set country code
  const setManualCountry = useCallback((newCountryCode) => {
    try {
      countryDetection.setCountryCode(newCountryCode);
      // State will be updated via the change listener
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  // Detect country from GPS coordinates
  const detectFromCoordinates = useCallback(async (lat, lon) => {
    try {
      const country = await countryDetection.detectFromCoordinates(lat, lon);
      if (country && country !== countryCode) {
        setCountryCode(country);
        setDetectionInfo(countryDetection.getDetectionInfo());
        
        if (optionsRef.current.onCountryChanged) {
          optionsRef.current.onCountryChanged(country);
        }
      }
      return country;
    } catch (err) {
      console.warn('GPS-based country detection failed:', err);
      return null;
    }
  }, [countryCode]);

  return {
    countryCode,
    loading,
    error,
    detectionInfo,
    refreshCountry,
    setManualCountry,
    detectFromCoordinates,
    isDetected: !loading && !error,
  };
}

export default useCountryDetection;
