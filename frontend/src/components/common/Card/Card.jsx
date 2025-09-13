/**
 * Card Component
 * 
 * A flexible card container component for displaying content in a structured way.
 * Includes variants for different use cases in the trucking logistics app.
 */

import React from 'react';
import { cn } from '../../../utils';

const cardVariants = {
  default: 'card',
  hover: 'card card-hover',
  bordered: 'card border-2',
  outlined: 'bg-transparent border border-neutral-300 rounded-xl',
  elevated: 'card shadow-lg',
};

const Card = React.forwardRef(({
  children,
  className,
  variant = 'default',
  padding = true,
  header,
  footer,
  title,
  subtitle,
  headerAction,
  ...props
}, ref) => {
  const cardClasses = cn(
    cardVariants[variant],
    className
  );

  return (
    <div ref={ref} className={cardClasses} {...props}>
      {/* Header section */}
      {(header || title || subtitle || headerAction) && (
        <div className={cn(
          'flex items-start justify-between',
          padding ? 'px-6 py-4 border-b border-neutral-200' : 'border-b border-neutral-200'
        )}>
          <div className="flex-1 min-w-0">
            {/* Title */}
            {title && (
              <h3 className="text-lg font-semibold text-neutral-900 truncate">
                {title}
              </h3>
            )}
            
            {/* Subtitle */}
            {subtitle && (
              <p className="text-sm text-neutral-500 mt-1">
                {subtitle}
              </p>
            )}
            
            {/* Custom header */}
            {header}
          </div>
          
          {/* Header action */}
          {headerAction && (
            <div className="flex-shrink-0 ml-4">
              {headerAction}
            </div>
          )}
        </div>
      )}
      
      {/* Content section */}
      <div className={cn(
        padding && 'px-6 py-4'
      )}>
        {children}
      </div>
      
      {/* Footer section */}
      {footer && (
        <div className={cn(
          'border-t border-neutral-200',
          padding ? 'px-6 py-4' : ''
        )}>
          {footer}
        </div>
      )}
    </div>
  );
});

Card.displayName = 'Card';

// Card Header subcomponent
const CardHeader = ({ children, className, ...props }) => (
  <div className={cn('px-6 py-4 border-b border-neutral-200', className)} {...props}>
    {children}
  </div>
);

CardHeader.displayName = 'CardHeader';

// Card Content subcomponent
const CardContent = ({ children, className, ...props }) => (
  <div className={cn('px-6 py-4', className)} {...props}>
    {children}
  </div>
);

CardContent.displayName = 'CardContent';

// Card Footer subcomponent
const CardFooter = ({ children, className, ...props }) => (
  <div className={cn('px-6 py-4 border-t border-neutral-200', className)} {...props}>
    {children}
  </div>
);

CardFooter.displayName = 'CardFooter';

// Card Title subcomponent
const CardTitle = ({ children, className, ...props }) => (
  <h3 className={cn('text-lg font-semibold text-neutral-900', className)} {...props}>
    {children}
  </h3>
);

CardTitle.displayName = 'CardTitle';

// Card Description subcomponent
const CardDescription = ({ children, className, ...props }) => (
  <p className={cn('text-sm text-neutral-500', className)} {...props}>
    {children}
  </p>
);

CardDescription.displayName = 'CardDescription';

export default Card;
export { CardHeader, CardContent, CardFooter, CardTitle, CardDescription, cardVariants };
