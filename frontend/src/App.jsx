/**
 * Main App Component
 * 
 * Showcases the Phase 1 implementation with design system and common components.
 * This will be replaced with the full trucking logistics interface in later phases.
 */

import React, { useState } from 'react';
import { 
  Button, 
  Input, 
  Card, 
  CardHeader, 
  CardContent, 
  CardTitle, 
  CardDescription,
  Loading,
  LoadingSkeleton 
} from './components';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState('');

  const handleTestLoading = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 3000);
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);
    
    // Simple validation example
    if (value.length > 0 && value.length < 3) {
      setInputError('Value must be at least 3 characters long');
    } else {
      setInputError('');
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50 py-8 px-4">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-neutral-900">
            Trucking Logistics App
          </h1>
          <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
            ELD Compliance & Route Planning System - Phase 1 Design System
          </p>
        </div>

        {/* Design System Showcase */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Colors Card */}
          <Card title="Color System" subtitle="Professional trucking industry palette">
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-neutral-700 mb-2">Primary Colors</h4>
                <div className="flex space-x-2">
                  <div className="w-12 h-12 bg-primary-500 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-primary-600 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-primary-700 rounded-lg shadow-sm"></div>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-neutral-700 mb-2">Secondary Colors (Safety Orange)</h4>
                <div className="flex space-x-2">
                  <div className="w-12 h-12 bg-secondary-500 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-secondary-600 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-secondary-700 rounded-lg shadow-sm"></div>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-neutral-700 mb-2">Status Colors</h4>
                <div className="flex space-x-2">
                  <div className="w-12 h-12 bg-success-500 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-warning-500 rounded-lg shadow-sm"></div>
                  <div className="w-12 h-12 bg-error-500 rounded-lg shadow-sm"></div>
                </div>
              </div>
            </div>
          </Card>

          {/* Typography Card */}
          <Card title="Typography" subtitle="Inter font family with proper hierarchy">
            <div className="space-y-3">
              <div className="text-4xl font-bold text-neutral-900">Heading 1</div>
              <div className="text-2xl font-semibold text-neutral-800">Heading 2</div>
              <div className="text-lg font-medium text-neutral-700">Heading 3</div>
              <div className="text-base text-neutral-600">Body text with proper line height and readability</div>
              <div className="text-sm text-neutral-500">Small text for helper content</div>
              <div className="font-mono text-sm text-neutral-700 bg-neutral-100 px-2 py-1 rounded">
                Monospace for data: 70:00:00
              </div>
            </div>
          </Card>
        </div>

        {/* Button Components */}
        <Card title="Button Components" subtitle="Accessible buttons with multiple variants and sizes">
          <div className="space-y-6">
            {/* Button Variants */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">Variants</h4>
              <div className="flex flex-wrap gap-3">
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="success">Success</Button>
                <Button variant="danger">Danger</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="link">Link</Button>
              </div>
            </div>

            {/* Button Sizes */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">Sizes (Touch-Friendly)</h4>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="xs">Extra Small</Button>
                <Button size="sm">Small</Button>
                <Button size="md">Medium</Button>
                <Button size="lg">Large</Button>
                <Button size="xl">Extra Large</Button>
              </div>
            </div>

            {/* Button States */}
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">States & Features</h4>
              <div className="flex flex-wrap gap-3">
                <Button disabled>Disabled</Button>
                <Button loading={loading} onClick={handleTestLoading}>
                  {loading ? 'Loading...' : 'Test Loading'}
                </Button>
                <Button fullWidth>Full Width Button</Button>
              </div>
            </div>
          </div>
        </Card>

        {/* Input Components */}
        <Card title="Input Components" subtitle="Form inputs with validation and accessibility">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="Driver Name"
                placeholder="Enter driver name"
                required
                helperText="Full legal name as appears on CDL"
              />
              
              <Input
                label="Current Cycle Hours"
                type="number"
                placeholder="0.00"
                value={inputValue}
                onChange={handleInputChange}
                error={inputError}
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Input size="sm" placeholder="Small input" />
              <Input size="md" placeholder="Medium input (default)" />
              <Input size="lg" placeholder="Large input" />
            </div>
          </div>
        </Card>

        {/* Loading Components */}
        <Card title="Loading Components" subtitle="Various loading states and skeletons">
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">Loading Variants</h4>
              <div className="flex flex-wrap items-center gap-8">
                <div className="text-center space-y-2">
                  <Loading variant="spinner" />
                  <p className="text-xs text-neutral-500">Spinner</p>
                </div>
                <div className="text-center space-y-2">
                  <Loading variant="dots" />
                  <p className="text-xs text-neutral-500">Dots</p>
                </div>
                <div className="text-center space-y-2">
                  <Loading variant="bars" />
                  <p className="text-xs text-neutral-500">Bars</p>
                </div>
                <div className="text-center space-y-2">
                  <Loading variant="pulse" />
                  <p className="text-xs text-neutral-500">Pulse</p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">Loading Skeletons</h4>
              <div className="space-y-3 max-w-md">
                <LoadingSkeleton width="w-3/4" height="h-4" />
                <LoadingSkeleton width="w-full" height="h-4" />
                <LoadingSkeleton width="w-1/2" height="h-4" />
              </div>
            </div>
          </div>
        </Card>

        {/* Card Variants */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card variant="default" padding={false}>
            <CardHeader>
              <CardTitle>Default Card</CardTitle>
              <CardDescription>Standard card with soft shadow</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-600">
                This is the standard card variant used throughout the application.
              </p>
            </CardContent>
          </Card>

          <Card variant="hover" padding={false}>
            <CardHeader>
              <CardTitle>Hover Card</CardTitle>
              <CardDescription>Interactive card with hover effects</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-600">
                Hover over this card to see the lift animation effect.
              </p>
            </CardContent>
          </Card>

          <Card variant="elevated" padding={false}>
            <CardHeader>
              <CardTitle>Elevated Card</CardTitle>
              <CardDescription>Card with stronger shadow</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-neutral-600">
                Used for important content that needs emphasis.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Status Badges */}
        <Card title="Status System" subtitle="Compliance and status indicators for trucking operations">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">HOS Compliance Status</h4>
              <div className="flex flex-wrap gap-3">
                <span className="badge-success">Compliant</span>
                <span className="badge-warning">Warning - 90% Used</span>
                <span className="badge-error">Violation - Over Limit</span>
                <span className="badge-info">Information</span>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-neutral-700 mb-3">Compliance Text Colors</h4>
              <div className="space-y-2">
                <p className="text-compliance-success">✓ All HOS limits are within compliance</p>
                <p className="text-compliance-warning">⚠ Approaching 70-hour weekly limit</p>
                <p className="text-compliance-danger">✗ Driving time exceeded - Violation logged</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center py-8">
          <p className="text-sm text-neutral-500">
            Phase 1 Complete: Foundation, Design System, and Common Components
          </p>
          <p className="text-xs text-neutral-400 mt-2">
            Next: Phase 2 - Core Features (Forms, Maps, ELD Logs)
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
