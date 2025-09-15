/**
 * Interactive OpenStreetMap Component with Real Mapping
 * 
 * Features:
 * - Real OpenStreetMap tiles
 * - Interactive pan/zoom
 * - Route polylines
 * - Pickup/Dropoff markers
 * - Current location marker
 * - Fuel stops and rest breaks
 */

import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, MapPin, Fuel, Coffee, Truck, Clock } from 'lucide-react';

// Fix for default markers in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons
const createIcon = (color, symbol) => L.divIcon({
  html: `<div style="
    width: 32px; 
    height: 32px; 
    border-radius: 50%; 
    background: ${color}; 
    border: 3px solid white; 
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    font-size: 12px;
  ">${symbol}</div>`,
  className: 'custom-marker',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const currentLocationIcon = createIcon('#10b981', '📍');
const pickupIcon = createIcon('#f59e0b', '📦');
const dropoffIcon = createIcon('#ef4444', '🚚');
const fuelIcon = createIcon('#8b5cf6', '⛽');
const restIcon = createIcon('#06b6d4', '☕');


// Component to fit map bounds to route
const FitBounds = ({ bounds }) => {
  const map = useMap();
  
  useEffect(() => {
    if (bounds && bounds.length > 0) {
      const leafletBounds = L.latLngBounds(bounds);
      map.fitBounds(leafletBounds, { padding: [20, 20] });
    }
  }, [bounds, map]);
  
  return null;
};

const InteractiveMap = ({ tripData, routeData, loading = false, className = '' }) => {
  const [mapCenter, setMapCenter] = useState([39.0458, -76.6413]); // Default to Baltimore, MD (trucking hub)
  const [mapBounds, setMapBounds] = useState([]);
  const [routeCoordinates, setRouteCoordinates] = useState([]);
  const [locations, setLocations] = useState({
    current: null,
    pickup: null,
    dropoff: null
  });

  // Process location data and create coordinates
  useEffect(() => {
    if (!tripData) return;

    console.log('🗺️ Processing trip data for map:', tripData);
    console.log('📍 Available locations:', tripData.locations);

    const newLocations = {};
    const bounds = [];

    // Process current location - handle both coordinate formats
    if (tripData.locations?.current) {
      const coords = tripData.locations.current.coordinates || tripData.locations.current;
      const lat = parseFloat(coords.lat || coords.latitude);
      const lon = parseFloat(coords.lon || coords.lng || coords.longitude);
      
      if (!isNaN(lat) && !isNaN(lon)) {
        const current = [lat, lon];
        newLocations.current = current;
        bounds.push(current);
        console.log('✅ Current location processed:', current);
      } else {
        console.warn('⚠️ Invalid current location coordinates:', coords);
      }
    }

    // Process pickup location - handle both coordinate formats  
    if (tripData.locations?.pickup) {
      const coords = tripData.locations.pickup.coordinates || tripData.locations.pickup;
      const lat = parseFloat(coords.lat || coords.latitude);
      const lon = parseFloat(coords.lon || coords.lng || coords.longitude);
      
      if (!isNaN(lat) && !isNaN(lon)) {
        const pickup = [lat, lon];
        newLocations.pickup = pickup;
        bounds.push(pickup);
        console.log('✅ Pickup location processed:', pickup);
      } else {
        console.warn('⚠️ Invalid pickup location coordinates:', coords);
      }
    }

    // Process dropoff location - handle both coordinate formats
    if (tripData.locations?.dropoff) {
      const coords = tripData.locations.dropoff.coordinates || tripData.locations.dropoff;
      const lat = parseFloat(coords.lat || coords.latitude);
      const lon = parseFloat(coords.lon || coords.lng || coords.longitude);
      
      if (!isNaN(lat) && !isNaN(lon)) {
        const dropoff = [lat, lon];
        newLocations.dropoff = dropoff;
        bounds.push(dropoff);
        console.log('✅ Dropoff location processed:', dropoff);
      } else {
        console.warn('⚠️ Invalid dropoff location coordinates:', coords);
      }
    }

    setLocations(newLocations);
    
    if (bounds.length > 0) {
      setMapBounds(bounds);
      // Set center to pickup location or first available location
      setMapCenter(newLocations.pickup || newLocations.current || bounds[0]);
    }

    console.log('✅ Processed locations:', newLocations);
    console.log('📍 Map bounds:', bounds);
  }, [tripData]);

  // Process route data and waypoints
  useEffect(() => {
    if (!routeData && !tripData) return;

    console.log('🛣️ Processing route data:', routeData);
    console.log('🎯 Processing waypoints from routeData:', routeData?.waypoints);
    console.log('🎯 Processing waypoints from tripData:', tripData?.waypoints);

    let coordinates = [];

    // PRIORITY 1: Use route geometry for detailed path (NOT waypoints)
    if (routeData?.route_geometry || routeData?.geometry) {
      try {
        let geometry = routeData.route_geometry || routeData.geometry;
        console.log('🔍 Raw geometry data:', geometry);
        console.log('🔍 Geometry type:', typeof geometry);
        
        // Handle different geometry formats
        if (typeof geometry === 'string') {
          // First try to parse as JSON (GeoJSON format)
          try {
            const parsed = JSON.parse(geometry);
            if (parsed.type === 'LineString' && parsed.coordinates) {
              // GeoJSON LineString format: [[lng, lat], [lng, lat], ...]
              coordinates = parsed.coordinates.map(coord => {
                // Convert from [lng, lat] to [lat, lng] for Leaflet
                return [parseFloat(coord[1]), parseFloat(coord[0])];
              });
              console.log('✅ Parsed GeoJSON LineString:', coordinates.length, 'points');
            } else if (Array.isArray(parsed)) {
              // Array of coordinates
              coordinates = parsed.map(coord => [parseFloat(coord[1]), parseFloat(coord[0])]);
              console.log('✅ Parsed coordinate array:', coordinates.length, 'points');
            }
          } catch (jsonError) {
            // If JSON parsing fails, try WKT format
            if (geometry.startsWith('LINESTRING')) {
              const coords = geometry.replace('LINESTRING(', '').replace(')', '');
              coordinates = coords.split(',').map(point => {
                const [lon, lat] = point.trim().split(' ').map(parseFloat);
                return [lat, lon]; // Leaflet uses [lat, lon]
              });
              console.log('✅ Parsed WKT LINESTRING:', coordinates.length, 'points');
            } else {
              console.warn('⚠️ Could not parse geometry string format:', jsonError.message);
            }
          }
        } else if (typeof geometry === 'object' && geometry.type === 'LineString') {
          // Direct GeoJSON object
          coordinates = geometry.coordinates.map(coord => [parseFloat(coord[1]), parseFloat(coord[0])]);
          console.log('✅ Parsed GeoJSON object:', coordinates.length, 'points');
        } else if (Array.isArray(geometry)) {
          // Direct array of coordinates
          coordinates = geometry.map(coord => [parseFloat(coord[1]), parseFloat(coord[0])]);
          console.log('✅ Parsed coordinate array:', coordinates.length, 'points');
        }
        
        console.log('✅ Route coordinates processed:', coordinates.length, 'points');
      } catch (error) {
        console.error('❌ Could not parse route geometry:', error);
        console.error('❌ Geometry data was:', routeData?.route_geometry || routeData?.geometry);
      }
    }
    
    // FALLBACK: If no detailed geometry, create simple route line between locations
    if (coordinates.length === 0 && locations.current && locations.pickup && locations.dropoff) {
      coordinates = [locations.current, locations.pickup, locations.dropoff];
      console.log('📍 Created simple route from locations:', coordinates.length, 'points');
    }
    
    // ADDITIONAL FALLBACK: If still no coordinates, use waypoints for basic path
    if (coordinates.length === 0) {
      // Only use waypoints as absolute last resort for route path
      if (routeData?.waypoints && Array.isArray(routeData.waypoints) && routeData.waypoints.length > 0) {
        coordinates = routeData.waypoints
          .filter(waypoint => {
            // Filter out waypoints with invalid coordinates (0,0 or NaN)
            const lat = parseFloat(waypoint.latitude || waypoint.lat);
            const lon = parseFloat(waypoint.longitude || waypoint.lon || waypoint.lng);
            return !isNaN(lat) && !isNaN(lon) && lat !== 0 && lon !== 0;
          })
          .map(waypoint => {
            const lat = parseFloat(waypoint.latitude || waypoint.lat);
            const lon = parseFloat(waypoint.longitude || waypoint.lon || waypoint.lng);
            return [lat, lon];
          });
        console.log('⚠️ Using waypoints as fallback for route path:', coordinates.length, 'points');
      }
    }
    
    setRouteCoordinates(coordinates);
    console.log('🗺️ Final route coordinates for polyline:', coordinates.length, 'points');
  }, [routeData, tripData, locations]);

  if (!tripData) {
    return (
      <div className={`relative ${className}`}>
        {/* Map Header */}
        <div className="bg-white border border-neutral-200 rounded-t-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Navigation className="w-5 h-5 text-primary-600" />
              <h3 className="font-semibold text-neutral-900">Interactive Route Map</h3>
            </div>
            <div className="text-sm text-neutral-600">
              Ready for trip planning
            </div>
          </div>
        </div>

        {/* Demo Map */}
        <div style={{ height: '500px' }} className="border-l border-r border-neutral-200">
          <MapContainer
            center={mapCenter}
            zoom={6}
            style={{ height: '100%', width: '100%' }}
            className="z-0"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={18}
            />
          </MapContainer>
        </div>

        {/* Map Footer */}
        <div className="bg-white border border-neutral-200 rounded-b-lg p-3">
          <div className="text-center text-neutral-500">
            <p className="text-sm">Enter trip details to view route with waypoints</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Map Header - Simplified */}
      <div className="bg-white border border-neutral-200 rounded-t-lg p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Navigation className="w-4 h-4 text-primary-600" />
            <h3 className="font-medium text-neutral-900">Route Map</h3>
          </div>
          <div className="text-sm text-neutral-600 flex items-center space-x-3">
            {tripData.estimatedDistance && (
              <span>{Math.round(parseFloat(tripData.estimatedDistance))} mi</span>
            )}
            {tripData.estimatedDuration && (
              <span>{parseFloat(tripData.estimatedDuration).toFixed(1)} hrs</span>
            )}
          </div>
        </div>
      </div>

      {/* OpenStreetMap Container */}
      <div style={{ height: '500px' }} className="border-l border-r border-neutral-200 relative">
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-3"></div>
              <p className="text-sm text-neutral-600">Calculating route...</p>
            </div>
          </div>
        )}
        
        <MapContainer
          center={mapCenter}
          zoom={8}
          style={{ height: '100%', width: '100%' }}
          className="z-0"
        >
          {/* OpenStreetMap Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />
          
          {/* Fit bounds to show all locations */}
          <FitBounds bounds={mapBounds} />
          
          {/* Current Location Marker */}
          {locations.current && (
            <Marker position={locations.current} icon={currentLocationIcon}>
              <Popup>
                <div className="text-center">
                  <strong>📍 Current</strong>
                  <br />
                  <span className="text-xs text-neutral-600">
                    {tripData.currentLocation}
                  </span>
                </div>
              </Popup>
            </Marker>
          )}
          
          {/* Pickup Location Marker */}
          {locations.pickup && (
            <Marker position={locations.pickup} icon={pickupIcon}>
              <Popup>
                <div className="text-center">
                  <strong>📦 Pickup</strong>
                  <br />
                  <span className="text-xs text-neutral-600">
                    {tripData.pickupLocation}
                  </span>
                </div>
              </Popup>
            </Marker>
          )}
          
          {/* Dropoff Location Marker */}
          {locations.dropoff && (
            <Marker position={locations.dropoff} icon={dropoffIcon}>
              <Popup>
                <div className="text-center">
                  <strong>🚚 Delivery</strong>
                  <br />
                  <span className="text-xs text-neutral-600">
                    {tripData.dropoffLocation}
                  </span>
                </div>
              </Popup>
            </Marker>
          )}
          
          {/* Route Polyline with Waypoints */}
          {routeCoordinates.length > 1 && (
            <Polyline
              positions={routeCoordinates}
              color="#3b82f6"
              weight={4}
              opacity={0.8}
            />
          )}
          
          
          
          {/* Waypoint Markers (Fuel Stops, Rest Breaks, etc.) */}
          {routeData?.waypoints && routeData.waypoints.map((waypoint, index) => {
            const lat = parseFloat(waypoint.latitude);
            const lon = parseFloat(waypoint.longitude);
            
            // Skip waypoints with invalid coordinates (0,0 or NaN)
            if (isNaN(lat) || isNaN(lon) || (lat === 0 && lon === 0)) {
              return null;
            }
            
            const position = [lat, lon];
            let icon, title, description;
            
            // Determine marker type based on waypoint_type
            switch(waypoint.waypoint_type) {
              case 'fuel_stop':
                icon = fuelIcon;
                title = '⛽ Fuel Stop';
                description = waypoint.description || 'Recommended fuel stop';
                break;
              case 'break_30min':
                icon = restIcon;
                title = '☕ 30-Min Break';
                description = waypoint.description || 'Mandatory 30-minute rest break';
                break;
              case 'break_10hour':
                icon = restIcon;
                title = '🛏️ 10-Hour Rest';
                description = waypoint.description || 'Mandatory 10-hour rest period';
                break;
              case 'origin':
                icon = currentLocationIcon;
                title = '📍 Origin';
                description = waypoint.description || 'Trip starting point';
                break;
              case 'pickup':
                icon = pickupIcon;
                title = '📦 Pickup';
                description = waypoint.description || 'Cargo pickup location';
                break;
              case 'dropoff':
                icon = dropoffIcon;
                title = '🚚 Delivery';
                description = waypoint.description || 'Cargo delivery location';
                break;
              default:
                icon = restIcon;
                title = '📍 Waypoint';
                description = waypoint.description || 'Route waypoint';
            }
            
            return (
              <Marker key={waypoint.id || `waypoint-${index}`} position={position} icon={icon}>
                <Popup>
                  <div className="text-center min-w-32">
                    <strong>{title}</strong>
                    <br />
                    <span className="text-xs text-neutral-600">
                      {description}
                    </span>
                    {waypoint.estimated_stop_duration_minutes && (
                      <>
                        <br />
                        <span className="text-xs font-medium text-primary-600">
                          Duration: {waypoint.estimated_stop_duration_minutes} min
                        </span>
                      </>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* Simplified Footer */}
      <div className="bg-white border border-neutral-200 rounded-b-lg p-2">
        <div className="flex items-center justify-center space-x-4 text-xs text-neutral-500">
          <span>🟢 Current</span>
          <span>🟡 Pickup</span>
          <span>🔴 Delivery</span>
          {routeData?.waypoints && routeData.waypoints.some(w => w.waypoint_type === 'fuel_stop') && <span>⛽ Fuel</span>}
          {routeData?.waypoints && routeData.waypoints.some(w => w.waypoint_type.includes('break')) && <span>☕ Rest</span>}
        </div>
      </div>
    </div>
  );
};

export default InteractiveMap;