/**
 * Utility functions for the Trucking Logistics App
 */

import { clsx } from 'clsx';

/**
 * Combines and merges CSS classes
 * Simple version using only clsx (tailwind-merge will be added in Phase 2)
 */
export function cn(...inputs) {
  return clsx(inputs);
}

/**
 * Format time to display hours and minutes
 * @param {number} hours - Time in hours (can be decimal)
 * @returns {string} Formatted time string (e.g., "8:30" or "11:00")
 */
export function formatTime(hours) {
  if (hours === null || hours === undefined || isNaN(hours)) return '--:--';
  
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  
  return `${wholeHours}:${minutes.toString().padStart(2, '0')}`;
}

/**
 * Format duration in minutes to hours and minutes
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration (e.g., "2h 30m" or "45m")
 */
export function formatDuration(minutes) {
  if (minutes === null || minutes === undefined || isNaN(minutes)) return '--';
  
  if (minutes < 60) {
    return `${minutes}m`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (remainingMinutes === 0) {
    return `${hours}h`;
  }
  
  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Calculate remaining hours for HOS compliance
 * @param {number} currentHours - Current hours used
 * @param {number} maxHours - Maximum allowed hours
 * @returns {number} Remaining hours
 */
export function calculateRemainingHours(currentHours, maxHours) {
  return Math.max(0, maxHours - currentHours);
}

/**
 * Determine compliance status based on hours used and limits
 * @param {number} currentHours - Current hours used
 * @param {number} maxHours - Maximum allowed hours
 * @param {number} warningThreshold - Warning threshold (0.8 = 80%)
 * @returns {'compliant' | 'warning' | 'violation'} Compliance status
 */
export function getComplianceStatus(currentHours, maxHours, warningThreshold = 0.8) {
  if (currentHours >= maxHours) return 'violation';
  if (currentHours >= maxHours * warningThreshold) return 'warning';
  return 'compliant';
}

/**
 * Get compliance status color class
 * @param {'compliant' | 'warning' | 'violation'} status - Compliance status
 * @returns {string} Tailwind CSS color class
 */
export function getComplianceColor(status) {
  switch (status) {
    case 'violation':
      return 'text-error-600';
    case 'warning':
      return 'text-warning-600';
    case 'compliant':
      return 'text-success-600';
    default:
      return 'text-neutral-600';
  }
}

/**
 * Get compliance badge classes
 * @param {'compliant' | 'warning' | 'violation'} status - Compliance status
 * @returns {string} Tailwind CSS badge classes
 */
export function getComplianceBadgeClasses(status) {
  switch (status) {
    case 'violation':
      return 'badge-error';
    case 'warning':
      return 'badge-warning';
    case 'compliant':
      return 'badge-success';
    default:
      return 'badge-info';
  }
}

/**
 * Format distance in miles
 * @param {number} miles - Distance in miles
 * @returns {string} Formatted distance string
 */
export function formatDistance(miles) {
  if (miles === null || miles === undefined || isNaN(miles)) return '--';
  
  if (miles < 1) {
    const feet = Math.round(miles * 5280);
    return `${feet} ft`;
  }
  
  return `${miles.toFixed(1)} mi`;
}

/**
 * Debounce function to limit the frequency of function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Generate a unique ID
 * @param {string} prefix - Optional prefix for the ID
 * @returns {string} Unique ID
 */
export function generateId(prefix = '') {
  const id = Math.random().toString(36).substring(2, 15) + 
             Math.random().toString(36).substring(2, 15);
  return prefix ? `${prefix}_${id}` : id;
}

/**
 * Check if a value is empty (null, undefined, empty string, empty array)
 * @param {any} value - Value to check
 * @returns {boolean} True if empty
 */
export function isEmpty(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * Capitalize first letter of a string
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
export function capitalize(str) {
  if (!str || typeof str !== 'string') return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid email format
 */
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Get current timestamp in ISO format
 * @returns {string} ISO timestamp
 */
export function getCurrentTimestamp() {
  return new Date().toISOString();
}

/**
 * Sleep function for async operations
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise} Promise that resolves after delay
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
