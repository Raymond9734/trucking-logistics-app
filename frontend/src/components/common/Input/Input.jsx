/**
 * Input Component
 * 
 * A flexible, accessible input component with validation states and proper labeling.
 * Optimized for trucking industry forms with large touch targets and clear error states.
 */

import React from 'react';
import { cn } from '../../../utils';

const inputSizes = {
  sm: 'px-3 py-2 text-sm h-9',
  md: 'px-4 py-2.5 text-base h-11',
  lg: 'px-4 py-3 text-lg h-12',
};

const Input = React.forwardRef(({
  label,
  error,
  helperText,
  required = false,
  size = 'md',
  fullWidth = true,
  leftIcon = null,
  rightIcon = null,
  className,
  containerClassName,
  labelClassName,
  id,
  type = 'text',
  disabled = false,
  placeholder,
  ...props
}, ref) => {
  // Generate ID if not provided
  const inputId = id || `input-${Math.random().toString(36).substring(2, 15)}`;
  
  const inputClasses = cn(
    // Base input styles
    'input-base',
    
    // Size styles
    inputSizes[size],
    
    // Full width
    fullWidth && 'w-full',
    
    // Validation states
    error && 'input-error',
    
    // Left padding adjustment for icon
    leftIcon && 'pl-10',
    
    // Right padding adjustment for icon
    rightIcon && 'pr-10',
    
    // Disabled state
    disabled && 'disabled:opacity-50 disabled:cursor-not-allowed',
    
    // Custom className
    className
  );

  const containerClasses = cn(
    'space-y-1.5',
    fullWidth && 'w-full',
    containerClassName
  );

  return (
    <div className={containerClasses}>
      {/* Label */}
      {label && (
        <label
          htmlFor={inputId}
          className={cn(
            'block text-sm font-medium text-neutral-700',
            required && 'after:content-["*"] after:text-error-500 after:ml-1',
            disabled && 'text-neutral-500',
            labelClassName
          )}
        >
          {label}
        </label>
      )}
      
      {/* Input container */}
      <div className="relative">
        {/* Left icon */}
        {leftIcon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 pointer-events-none">
            {leftIcon}
          </div>
        )}
        
        {/* Input field */}
        <input
          ref={ref}
          id={inputId}
          type={type}
          disabled={disabled}
          placeholder={placeholder}
          className={inputClasses}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={
            error || helperText ? `${inputId}-description` : undefined
          }
          {...props}
        />
        
        {/* Right icon */}
        {rightIcon && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 pointer-events-none">
            {rightIcon}
          </div>
        )}
      </div>
      
      {/* Helper text or error */}
      {(error || helperText) && (
        <div
          id={`${inputId}-description`}
          className={cn(
            'text-sm',
            error ? 'text-error-600' : 'text-neutral-500'
          )}
        >
          {error || helperText}
        </div>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;

// Export sizes for external use
export { inputSizes };
