// Export all services from a single entry point - Phase 1 Complete
export { default as apiClient, apiService, apiUtils } from './api';
export { default as locationService } from './locationService';
export { default as countryDetection, CountryDetectionService } from './countryDetection';

// Phase 1 Integration Complete:
// ✅ apiService - Complete Django backend integration
// ✅ apiUtils - Utility functions for API patterns
// ✅ locationService - LocationIQ integration for geocoding
// ✅ countryDetection - GPS-based country detection
