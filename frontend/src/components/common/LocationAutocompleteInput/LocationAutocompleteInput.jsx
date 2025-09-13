/**
 * LocationAutocompleteInput Component
 * 
 * A comprehensive location input component with:
 * - LocationIQ API integration for autocomplete
 * - GPS location detection
 * - Keyboard navigation
 * - Trucking-friendly location filtering
 * - Accessibility features
 */

import React, { useState, useRef, useEffect, forwardRef } from 'react';
import { MapPin, Navigation, Search, Loader, AlertCircle, Truck } from 'lucide-react';
import { useLocationAutocomplete, useGeoLocation } from '../../../hooks';
import { cn } from '../../../utils';

const LocationAutocompleteInput = forwardRef(({
  label,
  placeholder = 'Enter location...',
  value = '',
  onChange,
  onLocationSelect,
  onGpsLocation,
  error,
  helperText,
  required = false,
  disabled = false,
  showGpsButton = true,
  truckFriendly = true,
  countryCode = 'us', // Now received dynamically from parent
  className,
  containerClassName,
  icon: CustomIcon,
  size = 'md',
  ...props
}, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [inputValue, setInputValue] = useState(value);
  
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  const suggestionRefs = useRef([]);
  
  // Combine refs
  const combinedRef = (element) => {
    inputRef.current = element;
    if (ref) {
      if (typeof ref === 'function') {
        ref(element);
      } else {
        ref.current = element;
      }
    }
  };

  // Location autocomplete hook
  const { 
    suggestions, 
    loading: searchLoading, 
    error: searchError, 
    searchLocation, 
    clearSuggestions 
  } = useLocationAutocomplete({
    truckFriendly,
    countryCode,
    limit: 5,
  });

  // GPS location hook
  const { 
    getCurrentLocation, 
    loading: gpsLoading, 
    error: gpsError,
    isSupported: gpsSupported 
  } = useGeoLocation();

  // Update internal value when prop changes
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Handle input change
  const handleInputChange = (e) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    onChange?.(e);
    
    if (newValue.trim()) {
      searchLocation(newValue);
      setIsOpen(true);
      setSelectedIndex(-1);
    } else {
      clearSuggestions();
      setIsOpen(false);
    }
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion, index) => {
    setInputValue(suggestion.displayName);
    setIsOpen(false);
    setSelectedIndex(-1);
    clearSuggestions();
    
    // Create a synthetic event for onChange
    const syntheticEvent = {
      target: { value: suggestion.displayName, name: props.name },
    };
    onChange?.(syntheticEvent);
    onLocationSelect?.(suggestion);
  };

  // Handle GPS location request
  const handleGpsLocation = async () => {
    if (!gpsSupported || gpsLoading) return;

    try {
      const location = await getCurrentLocation();
      onGpsLocation?.(location);
    } catch (error) {
      console.error('GPS location error:', error);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
        
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          handleSuggestionSelect(suggestions[selectedIndex], selectedIndex);
        }
        break;
        
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
        
      default:
        break;
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        inputRef.current && 
        !inputRef.current.contains(event.target) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setIsOpen(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedIndex >= 0 && suggestionRefs.current[selectedIndex]) {
      suggestionRefs.current[selectedIndex].scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  const Icon = CustomIcon || Search;
  const hasError = error || searchError;
  const isLoading = searchLoading || gpsLoading;

  const inputSizes = {
    sm: 'px-3 py-2 text-sm h-9',
    md: 'px-4 py-2.5 text-base h-11',
    lg: 'px-4 py-3 text-lg h-12',
  };

  return (
    <div className={cn('relative', containerClassName)}>
      {/* Label */}
      {label && (
        <label className={cn(
          'block text-sm font-medium text-neutral-700 mb-2',
          required && 'after:content-["*"] after:text-error-500 after:ml-1',
          disabled && 'text-neutral-500'
        )}>
          {label}
        </label>
      )}

      {/* Input Container */}
      <div className="relative">
        {/* Main Input */}
        <input
          {...props}
          ref={combinedRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => inputValue && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            // Base styles
            'w-full border rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            
            // Size
            inputSizes[size],
            
            // Icon padding
            'pl-10',
            showGpsButton && gpsSupported && 'pr-10',
            
            // States
            hasError && 'border-error-500 focus:ring-error-500 focus:border-error-500',
            disabled && 'bg-neutral-50 text-neutral-500 cursor-not-allowed',
            !hasError && !disabled && 'border-neutral-300 hover:border-neutral-400',
            
            className
          )}
        />

        {/* Left Icon */}
        <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
          {isLoading ? (
            <Loader className="w-4 h-4 text-neutral-400 animate-spin" />
          ) : (
            <Icon className="w-4 h-4 text-neutral-400" />
          )}
        </div>

        {/* GPS Button */}
        {showGpsButton && gpsSupported && (
          <button
            type="button"
            onClick={handleGpsLocation}
            disabled={disabled || gpsLoading}
            className={cn(
              'absolute right-3 top-1/2 transform -translate-y-1/2',
              'p-1 rounded-md transition-colors',
              'hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500',
              (disabled || gpsLoading) && 'opacity-50 cursor-not-allowed',
              gpsError && 'text-error-500',
              !gpsError && 'text-neutral-500 hover:text-primary-600'
            )}
            title="Use current location"
          >
            <Navigation className={cn('w-4 h-4', gpsLoading && 'animate-pulse')} />
          </button>
        )}

        {/* Autocomplete Dropdown */}
        {isOpen && suggestions.length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-lg shadow-lg max-h-60 overflow-auto"
          >
            {suggestions.map((suggestion, index) => (
              <div
                key={suggestion.id}
                ref={el => suggestionRefs.current[index] = el}
                onClick={() => handleSuggestionSelect(suggestion, index)}
                className={cn(
                  'px-4 py-3 cursor-pointer border-b border-neutral-100 last:border-b-0',
                  'hover:bg-neutral-50 transition-colors',
                  selectedIndex === index && 'bg-primary-50 text-primary-700',
                  'flex items-start space-x-3'
                )}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {suggestion.truckAccessible ? (
                    <Truck className="w-4 h-4 text-green-600" />
                  ) : (
                    <MapPin className="w-4 h-4 text-neutral-400" />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-neutral-900 truncate">
                    {suggestion.address.formatted.split(',')[0]}
                  </div>
                  <div className="text-sm text-neutral-500 truncate">
                    {suggestion.address.formatted.split(',').slice(1).join(',').trim()}
                  </div>
                  {truckFriendly && suggestion.truckAccessible && (
                    <div className="text-xs text-green-600 mt-1 flex items-center space-x-1">
                      <Truck className="w-3 h-3" />
                      <span>Truck accessible</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No results message */}
        {isOpen && !searchLoading && suggestions.length === 0 && inputValue.length >= 2 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-lg shadow-lg p-4 text-center text-neutral-500">
            No locations found for "{inputValue}"
          </div>
        )}
      </div>

      {/* Error Message */}
      {hasError && (
        <div className="mt-2 flex items-center space-x-2 text-sm text-error-600">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error || searchError}</span>
        </div>
      )}

      {/* Helper Text */}
      {helperText && !hasError && (
        <div className="mt-2 text-sm text-neutral-500">
          {helperText}
        </div>
      )}

      {/* GPS Error */}
      {gpsError && showGpsButton && (
        <div className="mt-2 text-xs text-error-500">
          GPS: {gpsError.message}
        </div>
      )}
    </div>
  );
});

LocationAutocompleteInput.displayName = 'LocationAutocompleteInput';

export default LocationAutocompleteInput;
