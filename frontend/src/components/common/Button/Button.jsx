/**
 * Button Component
 * 
 * A flexible, accessible button component with multiple variants and sizes.
 * Optimized for trucking industry UX with large touch targets and clear visual feedback.
 */

import React from 'react';
import { cn } from '../../../utils';

const buttonVariants = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  success: 'btn-success',
  danger: 'btn-danger',
  ghost: 'bg-transparent hover:bg-neutral-100 text-neutral-700 font-medium',
  link: 'bg-transparent hover:underline text-primary-600 font-medium p-0 h-auto shadow-none',
};

const buttonSizes = {
  xs: 'px-2 py-1 text-xs h-7 min-w-[28px]',
  sm: 'px-3 py-1.5 text-sm h-8 min-w-[32px]',
  md: 'px-4 py-2 text-base h-10 min-w-[40px]',
  lg: 'px-6 py-3 text-lg h-12 min-w-[48px]',
  xl: 'px-8 py-4 text-xl h-14 min-w-[56px]',
};

const Button = React.forwardRef(({
  children,
  className,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  leftIcon = null,
  rightIcon = null,
  type = 'button',
  onClick,
  ...props
}, ref) => {
  const baseClasses = cn(
    // Base button styles
    'inline-flex items-center justify-center gap-2',
    'rounded-lg font-medium transition-all duration-200 ease-in-out',
    'focus:outline-none focus:ring-2 focus:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    'active:transform active:scale-95',
    'touch-target', // Ensures minimum touch target size
    
    // Variant styles
    buttonVariants[variant],
    
    // Size styles
    buttonSizes[size],
    
    // Full width
    fullWidth && 'w-full',
    
    // Loading state
    loading && 'cursor-wait',
    
    // Custom className
    className
  );

  const handleClick = (e) => {
    if (disabled || loading) {
      e.preventDefault();
      return;
    }
    onClick?.(e);
  };

  return (
    <button
      ref={ref}
      type={type}
      className={baseClasses}
      disabled={disabled || loading}
      onClick={handleClick}
      {...props}
    >
      {/* Loading spinner */}
      {loading && (
        <div className="spinner w-4 h-4" />
      )}
      
      {/* Left icon */}
      {leftIcon && !loading && (
        <span className="flex-shrink-0">
          {leftIcon}
        </span>
      )}
      
      {/* Button text */}
      <span className={cn(
        'flex-1 text-center',
        (leftIcon || rightIcon || loading) && 'flex-none'
      )}>
        {children}
      </span>
      
      {/* Right icon */}
      {rightIcon && !loading && (
        <span className="flex-shrink-0">
          {rightIcon}
        </span>
      )}
    </button>
  );
});

Button.displayName = 'Button';

export default Button;

// Export variants and sizes for external use
export { buttonVariants, buttonSizes };
