/**
 * API Service Configuration
 * 
 * Axios configuration and base API setup for the trucking logistics app.
 * This will handle all HTTP communications with the Django backend.
 */

import axios from 'axios';

// Base API URL - will be configurable via environment variables
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30 seconds timeout for long route calculations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth tokens
apiClient.interceptors.request.use(
  (config) => {
    // Add authentication token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add request timestamp for debugging
    config.metadata = { startTime: new Date() };
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and logging
apiClient.interceptors.response.use(
  (response) => {
    // Calculate request duration for performance monitoring
    const endTime = new Date();
    const duration = endTime - response.config.metadata.startTime;
    console.log(`API Request to ${response.config.url} took ${duration}ms`);
    
    return response;
  },
  (error) => {
    // Handle different types of errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Unauthorized - clear auth and redirect to login
          localStorage.removeItem('authToken');
          window.location.href = '/login';
          break;
        case 403:
          // Forbidden - user doesn't have permission
          console.error('Access forbidden:', data.message);
          break;
        case 404:
          // Not found
          console.error('Resource not found:', error.config.url);
          break;
        case 500:
          // Server error
          console.error('Server error:', data.message);
          break;
        default:
          console.error('API Error:', data.message || 'Unknown error');
      }
    } else if (error.request) {
      // Network error
      console.error('Network error:', error.message);
    } else {
      // Other error
      console.error('Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// API service functions will be implemented in Phase 2
export const apiService = {
  // Route planning endpoints
  routes: {
    calculateRoute: (routeData) => apiClient.post('/routes/calculate', routeData),
    getRouteById: (id) => apiClient.get(`/routes/${id}`),
    // TODO: Implement in Phase 2
  },
  
  // HOS compliance endpoints
  hos: {
    getCurrentStatus: (driverId) => apiClient.get(`/hos/status/${driverId}`),
    updateCycleHours: (data) => apiClient.post('/hos/update', data),
    // TODO: Implement in Phase 2
  },
  
  // ELD log endpoints
  eld: {
    generateLog: (logData) => apiClient.post('/eld/generate', logData),
    getLogsByDate: (date) => apiClient.get(`/eld/logs?date=${date}`),
    // TODO: Implement in Phase 2
  },
  
  // Driver management endpoints
  drivers: {
    getProfile: (id) => apiClient.get(`/drivers/${id}`),
    updateProfile: (id, data) => apiClient.put(`/drivers/${id}`, data),
    // TODO: Implement in Phase 2
  },
};

export default apiClient;
