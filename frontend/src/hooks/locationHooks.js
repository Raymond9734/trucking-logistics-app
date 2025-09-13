/**
 * Location-related React Hooks
 * 
 * Hooks for handling geolocation, location autocomplete, and GPS functionality
 * specifically designed for trucking logistics applications.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { locationService } from '../services';
import { useDebounce } from './index';

/**
 * Hook for managing GPS geolocation
 * @param {Object} options - Geolocation options
 * @returns {Object} - { location, error, loading, getCurrentLocation, watchPosition, clearWatch }
 */
export function useGeoLocation(options = {}) {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const watchIdRef = useRef(null);

  const defaultOptions = useMemo(() => ({
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 5 * 60 * 1000, // 5 minutes
    ...options,
  }), [options.enableHighAccuracy, options.timeout, options.maximumAge]);

  // Check if geolocation is supported
  const isSupported = 'geolocation' in navigator;

  /**
   * Get current position once
   */
  const getCurrentLocation = useCallback(async () => {
    if (!isSupported) {
      const error = new Error('Geolocation is not supported by this browser');
      setError(error);
      throw error;
    }

    setLoading(true);
    setError(null);

    try {
      const position = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, defaultOptions);
      });

      const locationData = {
        lat: position.coords.latitude,
        lon: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: position.timestamp,
        altitude: position.coords.altitude,
        altitudeAccuracy: position.coords.altitudeAccuracy,
        heading: position.coords.heading,
        speed: position.coords.speed,
      };

      setLocation(locationData);
      setLoading(false);
      return locationData;
    } catch (err) {
      const error = new Error(
        err.code === 1 ? 'Location access denied by user' :
        err.code === 2 ? 'Position unavailable' :
        err.code === 3 ? 'Location request timed out' :
        'An unknown error occurred while retrieving location'
      );
      setError(error);
      setLoading(false);
      throw error;
    }
  }, [isSupported, defaultOptions]);

  /**
   * Start watching position changes
   */
  const watchPosition = useCallback(() => {
    if (!isSupported) {
      const error = new Error('Geolocation is not supported by this browser');
      setError(error);
      return null;
    }

    if (watchIdRef.current !== null) {
      return watchIdRef.current; // Already watching
    }

    setError(null);

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const locationData = {
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp,
          altitude: position.coords.altitude,
          altitudeAccuracy: position.coords.altitudeAccuracy,
          heading: position.coords.heading,
          speed: position.coords.speed,
        };
        setLocation(locationData);
      },
      (err) => {
        const error = new Error(
          err.code === 1 ? 'Location access denied by user' :
          err.code === 2 ? 'Position unavailable' :
          err.code === 3 ? 'Location request timed out' :
          'An unknown error occurred while retrieving location'
        );
        setError(error);
      },
      defaultOptions
    );

    return watchIdRef.current;
  }, [isSupported, defaultOptions]);

  /**
   * Stop watching position changes
   */
  const clearWatch = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearWatch();
    };
  }, [clearWatch]);

  return {
    location,
    error,
    loading,
    isSupported,
    getCurrentLocation,
    watchPosition,
    clearWatch,
  };
}

/**
 * Hook for location autocomplete functionality
 * @param {Object} options - Autocomplete options
 * @returns {Object} - { suggestions, loading, error, searchLocation, clearSuggestions }
 */
export function useLocationAutocomplete(options = {}) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  
  const debounceMs = options.debounceMs || parseInt(import.meta.env.VITE_AUTOCOMPLETE_DEBOUNCE_MS) || 300;
  const debouncedQuery = useDebounce(query, debounceMs);
  
  const abortControllerRef = useRef(null);

  // Memoize options to prevent infinite re-renders
  const searchOptions = useMemo(() => ({
    limit: options.limit || 5,
    countryCode: options.countryCode || 'us', // Will be passed dynamically from parent components
    truckFriendly: options.truckFriendly !== undefined ? options.truckFriendly : true,
    debounceMs: options.debounceMs || 300,
    ...options,
  }), [
    options.limit,
    options.countryCode,
    options.truckFriendly,
    options.debounceMs
  ]);

  /**
   * Search for location suggestions
   */
  const searchLocation = useCallback((searchQuery) => {
    setQuery(searchQuery);
    setError(null);
  }, []);

  /**
   * Clear suggestions
   */
  const clearSuggestions = useCallback(() => {
    setSuggestions([]);
    setQuery('');
    setError(null);
    setLoading(false);
    
    // Abort any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // Effect to handle debounced search
  useEffect(() => {
    const performSearch = async () => {
      if (!debouncedQuery || debouncedQuery.length < 2) {
        setSuggestions([]);
        return;
      }

      // Abort previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();
      setLoading(true);
      setError(null);

      try {
        const results = await locationService.autocomplete(debouncedQuery, {
          ...searchOptions,
          signal: abortControllerRef.current.signal,
        });
        
        setSuggestions(results);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setSuggestions([]);
        }
      } finally {
        setLoading(false);
        abortControllerRef.current = null;
      }
    };

    performSearch();
  }, [debouncedQuery, searchOptions]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    suggestions,
    loading,
    error,
    query,
    searchLocation,
    clearSuggestions,
  };
}

/**
 * Hook for reverse geocoding (coordinates to address)
 * @param {number} lat - Latitude
 * @param {number} lon - Longitude
 * @param {Object} options - Reverse geocoding options
 * @returns {Object} - { address, loading, error, refetch }
 */
export function useReverseGeocode(lat, lon, options = {}) {
  const [address, setAddress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Memoize options to prevent infinite re-renders
  const memoizedOptions = useMemo(() => options, [
    JSON.stringify(options)
  ]);

  const refetch = useCallback(async () => {
    if (!lat || !lon) {
      setAddress(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await locationService.reverseGeocode(lat, lon, memoizedOptions);
      setAddress(result);
    } catch (err) {
      setError(err.message);
      setAddress(null);
    } finally {
      setLoading(false);
    }
  }, [lat, lon, memoizedOptions]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return {
    address,
    loading,
    error,
    refetch,
  };
}

/**
 * Hook for combining GPS and reverse geocoding
 * @param {Object} options - Combined options
 * @returns {Object} - GPS location with address information
 */
export function useLocationWithAddress(options = {}) {
  // Memoize options to prevent unnecessary re-renders
  const gpsOptions = useMemo(() => options.gps || {}, [
    JSON.stringify(options.gps || {})
  ]);
  
  const reverseOptions = useMemo(() => options.reverse || {}, [
    JSON.stringify(options.reverse || {})
  ]);

  const { 
    location, 
    error: gpsError, 
    loading: gpsLoading, 
    getCurrentLocation 
  } = useGeoLocation(gpsOptions);
  
  const { 
    address, 
    loading: addressLoading, 
    error: addressError 
  } = useReverseGeocode(
    location?.lat, 
    location?.lon, 
    reverseOptions
  );

  const getCurrentLocationWithAddress = useCallback(async () => {
    const locationData = await getCurrentLocation();
    // Address will be automatically fetched via useReverseGeocode effect
    return { location: locationData, address };
  }, [getCurrentLocation, address]);

  return {
    location,
    address,
    loading: gpsLoading || addressLoading,
    error: gpsError || addressError,
    getCurrentLocationWithAddress,
  };
}

export default {
  useGeoLocation,
  useLocationAutocomplete,
  useReverseGeocode,
  useLocationWithAddress,
};
