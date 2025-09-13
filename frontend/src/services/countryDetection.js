/**
 * Country Detection Service
 * 
 * Automatically detects the user's country code based on:
 * 1. IP geolocation (primary method)
 * 2. Browser locale (fallback)
 * 3. GPS coordinates (if available)
 * 4. Manual override (stored in localStorage)
 */

// Free IP geolocation services (no API key required)
const IP_GEOLOCATION_APIS = [
  {
    name: 'ipapi.co',
    url: 'https://ipapi.co/json/',
    extractCountry: (data) => data.country_code?.toLowerCase(),
    rateLimit: 1000, // requests per day
  },
  {
    name: 'ip-api.com',
    url: 'http://ip-api.com/json/',
    extractCountry: (data) => data.countryCode?.toLowerCase(),
    rateLimit: 45, // requests per minute for free tier
  },
  {
    name: 'geolocation-db.com',
    url: 'https://geolocation-db.com/json/',
    extractCountry: (data) => data.country_code?.toLowerCase(),
    rateLimit: 15000, // requests per hour
  },
];

/**
 * Country detection cache and storage
 */
class CountryCache {
  constructor() {
    this.cacheKey = 'user_country_cache';
    this.ttl = 24 * 60 * 60 * 1000; // 24 hours
  }

  get() {
    try {
      const cached = localStorage.getItem(this.cacheKey);
      if (!cached) return null;

      const { country, timestamp, method } = JSON.parse(cached);
      
      // Check if cache is still valid
      if (Date.now() - timestamp < this.ttl) {
        return { country, method };
      }
      
      // Cache expired, remove it
      this.clear();
      return null;
    } catch (error) {
      console.warn('Error reading country cache:', error);
      this.clear();
      return null;
    }
  }

  set(country, method) {
    try {
      const data = {
        country: country?.toLowerCase(),
        method,
        timestamp: Date.now(),
      };
      localStorage.setItem(this.cacheKey, JSON.stringify(data));
    } catch (error) {
      console.warn('Error saving country cache:', error);
    }
  }

  clear() {
    try {
      localStorage.removeItem(this.cacheKey);
    } catch (error) {
      console.warn('Error clearing country cache:', error);
    }
  }
}

const countryCache = new CountryCache();

/**
 * Country Detection Service
 */
export class CountryDetectionService {
  constructor() {
    this.detectedCountry = null;
    this.detectionMethod = null;
    this.listeners = new Set();
  }

  /**
   * Get the user's country code (2-letter ISO code)
   * @returns {Promise<string>} Country code in lowercase (e.g., 'us', 'ke', 'gb')
   */
  async getCountryCode() {
    // Check if already detected in this session
    if (this.detectedCountry) {
      return this.detectedCountry;
    }

    // Check cache first
    const cached = countryCache.get();
    if (cached) {
      this.detectedCountry = cached.country;
      this.detectionMethod = cached.method;
      return this.detectedCountry;
    }

    // Detect country using multiple methods
    const country = await this.detectCountry();
    
    // Cache the result
    if (country) {
      countryCache.set(country, this.detectionMethod);
      this.detectedCountry = country;
      this.notifyListeners(country);
    }

    return country || 'us'; // Fallback to US
  }

  /**
   * Detect country using multiple methods
   * @returns {Promise<string|null>} Detected country code
   */
  async detectCountry() {
    const detectionMethods = [
      () => this.detectFromIP(),
      () => this.detectFromLocale(),
      () => this.detectFromTimezone(),
    ];

    for (const method of detectionMethods) {
      try {
        const country = await method();
        if (country && this.isValidCountryCode(country)) {
          return country.toLowerCase();
        }
      } catch (error) {
        console.warn(`Country detection method failed:`, error);
        continue; // Try next method
      }
    }

    return null;
  }

  /**
   * Detect country from IP geolocation
   * @returns {Promise<string|null>} Country code from IP
   */
  async detectFromIP() {
    // Try multiple IP geolocation services
    for (const api of IP_GEOLOCATION_APIS) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

        const response = await fetch(api.url, {
          signal: controller.signal,
          method: 'GET',
        });
        
        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          const country = api.extractCountry(data);
          
          if (country) {
            this.detectionMethod = `ip_${api.name}`;
            console.log(`🌍 Country detected from ${api.name}:`, country.toUpperCase());
            return country;
          }
        }
      } catch (error) {
        console.warn(`IP geolocation failed for ${api.name}:`, error);
        continue; // Try next service
      }
    }

    return null;
  }

  /**
   * Detect country from browser locale
   * @returns {string|null} Country code from locale
   */
  detectFromLocale() {
    try {
      // Get language-country from locale (e.g., "en-US" -> "US")
      const locale = navigator.language || navigator.languages?.[0];
      if (locale && locale.includes('-')) {
        const countryCode = locale.split('-')[1];
        if (countryCode && this.isValidCountryCode(countryCode)) {
          this.detectionMethod = 'browser_locale';
          console.log(`🌐 Country detected from locale:`, countryCode.toUpperCase());
          return countryCode.toLowerCase();
        }
      }

      // Try getting from Intl.Locale if available
      if (typeof Intl !== 'undefined' && Intl.Locale) {
        const intlLocale = new Intl.Locale(locale);
        if (intlLocale.region) {
          this.detectionMethod = 'intl_locale';
          console.log(`🌐 Country detected from Intl.Locale:`, intlLocale.region.toUpperCase());
          return intlLocale.region.toLowerCase();
        }
      }
    } catch (error) {
      console.warn('Locale-based country detection failed:', error);
    }

    return null;
  }

  /**
   * Detect country from timezone
   * @returns {string|null} Country code from timezone
   */
  detectFromTimezone() {
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      
      // Map common timezones to countries
      const timezoneCountryMap = {
        'America/New_York': 'us',
        'America/Los_Angeles': 'us',
        'America/Chicago': 'us',
        'America/Denver': 'us',
        'Europe/London': 'gb',
        'Europe/Paris': 'fr',
        'Europe/Berlin': 'de',
        'Europe/Madrid': 'es',
        'Europe/Rome': 'it',
        'Africa/Nairobi': 'ke',
        'Africa/Cairo': 'eg',
        'Africa/Lagos': 'ng',
        'Asia/Tokyo': 'jp',
        'Asia/Shanghai': 'cn',
        'Asia/Kolkata': 'in',
        'Australia/Sydney': 'au',
        'Australia/Melbourne': 'au',
      };

      const country = timezoneCountryMap[timezone];
      if (country) {
        this.detectionMethod = 'timezone';
        console.log(`🕐 Country detected from timezone (${timezone}):`, country.toUpperCase());
        return country;
      }

      // Try to extract country from timezone string
      const parts = timezone.split('/');
      if (parts.length >= 2) {
        const region = parts[0].toLowerCase();
        const regionCountryMap = {
          'america': 'us',
          'europe': 'gb', // Default to GB for Europe
          'africa': 'ke', // You're in Nairobi, so default to Kenya for Africa
          'asia': 'in',   // Default to India for Asia
          'australia': 'au',
        };
        
        const mappedCountry = regionCountryMap[region];
        if (mappedCountry) {
          this.detectionMethod = 'timezone_region';
          console.log(`🕐 Country detected from timezone region (${region}):`, mappedCountry.toUpperCase());
          return mappedCountry;
        }
      }
    } catch (error) {
      console.warn('Timezone-based country detection failed:', error);
    }

    return null;
  }

  /**
   * Detect country from GPS coordinates
   * @param {number} lat - Latitude
   * @param {number} lon - Longitude
   * @returns {Promise<string|null>} Country code from coordinates
   */
  async detectFromCoordinates(lat, lon) {
    try {
      // Use a simple coordinate-to-country mapping for major countries
      // For production, you'd use reverse geocoding service
      const coordinateRanges = {
        'us': { latMin: 25, latMax: 49, lonMin: -125, lonMax: -66 },
        'ke': { latMin: -5, latMax: 5, lonMin: 34, lonMax: 42 },
        'gb': { latMin: 50, latMax: 61, lonMin: -8, lonMax: 2 },
        'de': { latMin: 47, latMax: 55, lonMin: 6, lonMax: 15 },
        'fr': { latMin: 42, latMax: 51, lonMin: -5, lonMax: 8 },
        'in': { latMin: 8, latMax: 37, lonMin: 68, lonMax: 97 },
        'cn': { latMin: 18, latMax: 54, lonMin: 73, lonMax: 135 },
        'au': { latMin: -44, latMax: -10, lonMin: 113, lonMax: 154 },
      };

      for (const [country, range] of Object.entries(coordinateRanges)) {
        if (lat >= range.latMin && lat <= range.latMax && 
            lon >= range.lonMin && lon <= range.lonMax) {
          this.detectionMethod = 'gps_coordinates';
          console.log(`📍 Country detected from GPS coordinates:`, country.toUpperCase());
          return country;
        }
      }
    } catch (error) {
      console.warn('GPS-based country detection failed:', error);
    }

    return null;
  }

  /**
   * Validate country code format
   * @param {string} code - Country code to validate
   * @returns {boolean} Whether the code is valid
   */
  isValidCountryCode(code) {
    return typeof code === 'string' && code.length === 2 && /^[a-zA-Z]{2}$/.test(code);
  }

  /**
   * Manually set country code (user override)
   * @param {string} countryCode - 2-letter country code
   */
  setCountryCode(countryCode) {
    if (this.isValidCountryCode(countryCode)) {
      const country = countryCode.toLowerCase();
      this.detectedCountry = country;
      this.detectionMethod = 'manual_override';
      countryCache.set(country, this.detectionMethod);
      this.notifyListeners(country);
      console.log(`🎯 Country manually set to:`, country.toUpperCase());
    } else {
      throw new Error('Invalid country code format. Must be 2 letters.');
    }
  }

  /**
   * Clear cached country data and re-detect
   */
  async refreshCountry() {
    this.detectedCountry = null;
    this.detectionMethod = null;
    countryCache.clear();
    
    const country = await this.getCountryCode();
    console.log(`🔄 Country refreshed:`, country.toUpperCase());
    return country;
  }

  /**
   * Add listener for country changes
   * @param {Function} callback - Callback function
   */
  onCountryChange(callback) {
    this.listeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(callback);
    };
  }

  /**
   * Notify all listeners of country change
   * @param {string} country - New country code
   */
  notifyListeners(country) {
    this.listeners.forEach(callback => {
      try {
        callback(country);
      } catch (error) {
        console.warn('Error in country change listener:', error);
      }
    });
  }

  /**
   * Get detection information
   * @returns {Object} Detection details
   */
  getDetectionInfo() {
    return {
      country: this.detectedCountry,
      method: this.detectionMethod,
      cached: !!countryCache.get(),
    };
  }
}

// Create singleton instance
export const countryDetection = new CountryDetectionService();

// Auto-detect country on import
countryDetection.getCountryCode().then(country => {
  console.log(`🌍 Auto-detected user country: ${country.toUpperCase()}`);
}).catch(error => {
  console.warn('Failed to auto-detect country:', error);
});

export default countryDetection;
