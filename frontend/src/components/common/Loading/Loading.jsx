/**
 * Loading Component
 * 
 * A versatile loading component with multiple variants and sizes.
 * Used throughout the app to indicate loading states.
 */

import React from 'react';
import { cn } from '../../../utils';

const loadingVariants = {
  spinner: 'spinner',
  dots: 'flex space-x-1',
  bars: 'flex space-x-1',
  pulse: 'animate-pulse-soft',
};

const loadingSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
};

const Loading = ({
  variant = 'spinner',
  size = 'md',
  className,
  text,
  fullScreen = false,
  overlay = false,
  color = 'primary',
  ...props
}) => {
  const colorClasses = {
    primary: 'border-primary-600',
    secondary: 'border-secondary-600',
    neutral: 'border-neutral-600',
    white: 'border-white',
  };

  // Spinner variant
  const renderSpinner = () => (
    <div
      className={cn(
        'spinner',
        loadingSizes[size],
        color === 'primary' && 'border-neutral-300 border-t-primary-600',
        color === 'secondary' && 'border-neutral-300 border-t-secondary-600',
        color === 'neutral' && 'border-neutral-300 border-t-neutral-600',
        color === 'white' && 'border-white/30 border-t-white',
        className
      )}
      {...props}
    />
  );

  // Dots variant
  const renderDots = () => (
    <div className={cn('flex space-x-1', className)} {...props}>
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={cn(
            'rounded-full animate-pulse-soft',
            loadingSizes[size],
            color === 'primary' && 'bg-primary-600',
            color === 'secondary' && 'bg-secondary-600',
            color === 'neutral' && 'bg-neutral-600',
            color === 'white' && 'bg-white'
          )}
          style={{
            animationDelay: `${index * 0.2}s`,
            animationDuration: '1s',
          }}
        />
      ))}
    </div>
  );

  // Bars variant
  const renderBars = () => (
    <div className={cn('flex space-x-1 items-end', className)} {...props}>
      {[0, 1, 2, 3].map((index) => (
        <div
          key={index}
          className={cn(
            'rounded-sm animate-pulse-soft',
            size === 'xs' && 'w-1',
            size === 'sm' && 'w-1.5',
            size === 'md' && 'w-2',
            size === 'lg' && 'w-3',
            size === 'xl' && 'w-4',
            color === 'primary' && 'bg-primary-600',
            color === 'secondary' && 'bg-secondary-600',
            color === 'neutral' && 'bg-neutral-600',
            color === 'white' && 'bg-white'
          )}
          style={{
            height: `${12 + (index * 4)}px`,
            animationDelay: `${index * 0.1}s`,
            animationDuration: '0.8s',
          }}
        />
      ))}
    </div>
  );

  // Pulse variant
  const renderPulse = () => (
    <div
      className={cn(
        'rounded-lg animate-pulse-soft',
        loadingSizes[size],
        color === 'primary' && 'bg-primary-200',
        color === 'secondary' && 'bg-secondary-200',
        color === 'neutral' && 'bg-neutral-200',
        color === 'white' && 'bg-white/50',
        className
      )}
      {...props}
    />
  );

  const renderLoadingElement = () => {
    switch (variant) {
      case 'dots':
        return renderDots();
      case 'bars':
        return renderBars();
      case 'pulse':
        return renderPulse();
      case 'spinner':
      default:
        return renderSpinner();
    }
  };

  const loadingElement = (
    <div className="flex flex-col items-center justify-center space-y-3">
      {renderLoadingElement()}
      {text && (
        <p className={cn(
          'text-sm font-medium',
          color === 'white' ? 'text-white' : 'text-neutral-600'
        )}>
          {text}
        </p>
      )}
    </div>
  );

  // Full screen loading
  if (fullScreen) {
    return (
      <div className={cn(
        'fixed inset-0 z-50 flex items-center justify-center',
        overlay ? 'bg-white/80 backdrop-blur-sm' : 'bg-white'
      )}>
        {loadingElement}
      </div>
    );
  }

  // Overlay loading (positioned absolutely within parent)
  if (overlay) {
    return (
      <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 backdrop-blur-sm rounded-inherit">
        {loadingElement}
      </div>
    );
  }

  // Inline loading
  return loadingElement;
};

Loading.displayName = 'Loading';

// Loading skeleton component for content placeholders
const LoadingSkeleton = ({ 
  className, 
  width = 'w-full', 
  height = 'h-4',
  rounded = 'rounded',
  ...props 
}) => (
  <div
    className={cn(
      'animate-pulse-soft bg-neutral-200',
      width,
      height,
      rounded,
      className
    )}
    {...props}
  />
);

LoadingSkeleton.displayName = 'LoadingSkeleton';

export default Loading;
export { LoadingSkeleton, loadingVariants, loadingSizes };
