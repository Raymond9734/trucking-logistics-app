/**
 * LocationIQ Service
 * 
 * Provides location-related services using LocationIQ API
 * - Autocomplete search
 * - Geocoding (address to coordinates)
 * - Reverse geocoding (coordinates to address)
 * 
 * LocationIQ uses OpenStreetMap data and offers:
 * - 10,000 free requests per day
 * - Good coverage worldwide
 * - Trucking-friendly locations with proper filtering
 */

import axios from 'axios';

const API_KEY = import.meta.env.VITE_LOCATIONIQ_API_KEY;
const BASE_URL = import.meta.env.VITE_LOCATIONIQ_BASE_URL || 'https://api.locationiq.com/v1';

if (!API_KEY && import.meta.env.DEV) {
  console.warn('LocationIQ API key not found. Please set VITE_LOCATIONIQ_API_KEY in your .env file.');
}

// Create axios instance for LocationIQ API
const locationIQClient = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  params: {
    key: API_KEY,
  },
});

// Request interceptor for debugging
locationIQClient.interceptors.request.use((config) => {
  if (import.meta.env.VITE_DEBUG_MODE === 'true') {
    console.log(`LocationIQ API Request: ${config.method?.toUpperCase()} ${config.url}`, config.params);
  }
  return config;
});

// Response interceptor for error handling
locationIQClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('LocationIQ API Error:', error.response?.data || error.message);
    
    // Handle specific error cases
    if (error.response?.status === 401) {
      throw new Error('Invalid LocationIQ API key. Please check your configuration.');
    } else if (error.response?.status === 429) {
      throw new Error('LocationIQ API rate limit exceeded. Please try again later.');
    } else if (error.response?.status === 400) {
      throw new Error('Invalid search query. Please check your input.');
    } else if (error.code === 'ENOTFOUND' || error.code === 'NETWORK_ERROR') {
      throw new Error('Network error: Cannot reach LocationIQ servers. Please check your internet connection.');
    }
    
    throw new Error('Location service unavailable. Please try again later.');
  }
);

/**
 * Location cache for reducing API calls
 */
class LocationCache {
  constructor(maxSize = 100, ttl = 5 * 60 * 1000) { // 5 minutes TTL
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttl;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }

  set(key, data) {
    // Remove oldest entries if cache is full
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  clear() {
    this.cache.clear();
  }
}

const cache = new LocationCache();

/**
 * LocationIQ Service Implementation
 */
export const locationService = {
  /**
   * Search for location suggestions (autocomplete)
   * @param {string} query - Search query
   * @param {Object} options - Search options
   * @returns {Promise<Array>} Array of location suggestions
   */
  async autocomplete(query, options = {}) {
    if (!query || query.length < 2) return [];

    const cacheKey = `autocomplete:${query}:${JSON.stringify(options)}`;
    const cached = cache.get(cacheKey);
    if (cached) return cached;

    try {
      const params = {
        q: query,
        limit: options.limit || 5,
        countrycodes: options.countryCode || 'us', // Now dynamically passed from components
        normalizecity: 1, // Normalize city names
        ...options.params,
      };

      // Use the correct autocomplete endpoint
      const response = await locationIQClient.get('/autocomplete', { params });
      
      const suggestions = response.data.map(item => ({
        id: item.place_id,
        displayName: item.display_name,
        address: this.formatAddress(item),
        coordinates: {
          lat: parseFloat(item.lat),
          lon: parseFloat(item.lon),
        },
        type: item.type,
        category: item.category,
        importance: item.importance,
        // Additional trucking-relevant data
        boundingBox: item.boundingbox ? {
          north: parseFloat(item.boundingbox[1]),
          south: parseFloat(item.boundingbox[0]),
          east: parseFloat(item.boundingbox[3]),
          west: parseFloat(item.boundingbox[2]),
        } : null,
        // Check if location might be truck-accessible
        truckAccessible: this.assessTruckAccessibility(item),
        raw: item, // Keep original data for debugging
      }));

      cache.set(cacheKey, suggestions);
      return suggestions;
    } catch (error) {
      console.error('Autocomplete search failed:', error);
      throw error;
    }
  },

  /**
   * Geocode an address to coordinates (uses Search API)
   * @param {string} address - Address to geocode
   * @param {Object} options - Geocoding options
   * @returns {Promise<Object>} Geocoded location
   */
  async geocode(address, options = {}) {
    if (!address) throw new Error('Address is required for geocoding');

    const cacheKey = `geocode:${address}`;
    const cached = cache.get(cacheKey);
    if (cached) return cached;

    try {
      const params = {
        q: address,
        limit: 1,
        format: 'json',
        addressdetails: 1,
        ...options.params,
      };

      // Use the search endpoint for geocoding
      const response = await locationIQClient.get('/search.php', { params });
      
      if (!response.data.length) {
        throw new Error('Address not found');
      }

      const item = response.data[0];
      const result = {
        address: this.formatAddress(item),
        coordinates: {
          lat: parseFloat(item.lat),
          lon: parseFloat(item.lon),
        },
        displayName: item.display_name,
        type: item.type,
        importance: item.importance,
        truckAccessible: this.assessTruckAccessibility(item),
      };

      cache.set(cacheKey, result);
      return result;
    } catch (error) {
      console.error('Geocoding failed:', error);
      throw error;
    }
  },

  /**
   * Reverse geocode coordinates to address
   * @param {number} lat - Latitude
   * @param {number} lon - Longitude
   * @param {Object} options - Reverse geocoding options
   * @returns {Promise<Object>} Address information
   */
  async reverseGeocode(lat, lon, options = {}) {
    if (!lat || !lon) throw new Error('Latitude and longitude are required');

    const cacheKey = `reverse:${lat},${lon}`;
    const cached = cache.get(cacheKey);
    if (cached) return cached;

    try {
      const params = {
        lat,
        lon,
        format: 'json',
        addressdetails: 1,
        ...options.params,
      };

      const response = await locationIQClient.get('/reverse.php', { params });
      
      const result = {
        address: this.formatAddress(response.data),
        displayName: response.data.display_name,
        coordinates: { lat, lon },
        type: response.data.type,
        truckAccessible: this.assessTruckAccessibility(response.data),
      };

      cache.set(cacheKey, result);
      return result;
    } catch (error) {
      console.error('Reverse geocoding failed:', error);
      throw error;
    }
  },

  /**
   * Format LocationIQ address data into a structured format
   * @param {Object} item - LocationIQ response item
   * @returns {Object} Formatted address
   */
  formatAddress(item) {
    const addr = item.address || {};
    return {
      houseNumber: addr.house_number || '',
      street: addr.road || '',
      city: addr.city || addr.town || addr.village || '',
      state: addr.state || addr.region || '',
      postalCode: addr.postcode || '',
      country: addr.country || '',
      countryCode: addr.country_code || '',
      formatted: item.display_name || '',
    };
  },

  /**
   * Assess if a location is likely truck-accessible
   * @param {Object} item - LocationIQ response item
   * @returns {boolean} Whether location is likely truck accessible
   */
  assessTruckAccessibility(item) {
    const type = item.type?.toLowerCase() || '';
    const category = item.category?.toLowerCase() || '';
    
    // Define truck-friendly location types
    const truckFriendlyTypes = [
      'fuel', 'gas_station', 'truck_stop', 'rest_area',
      'industrial', 'warehouse', 'logistics', 'depot',
      'commercial', 'retail', 'supermarket', 'mall',
      'port', 'airport', 'terminal', 'distribution_center'
    ];

    // Check if it's a highway or major road
    const isHighway = type.includes('highway') || type.includes('trunk') || type.includes('primary');
    
    // Check if it's a truck-friendly category
    const isTruckFriendly = truckFriendlyTypes.some(friendlyType => 
      type.includes(friendlyType) || category.includes(friendlyType)
    );

    return isTruckFriendly || isHighway;
  },

  /**
   * Clear the location cache
   */
  clearCache() {
    cache.clear();
  },

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return {
      size: cache.cache.size,
      maxSize: cache.maxSize,
      ttl: cache.ttl,
    };
  },
};

export default locationService;