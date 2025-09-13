/**
 * Main Application Layout Component
 * 
 * Provides the overall structure for the trucking logistics app with
 * navigation, header with HOS status, and main content area.
 */

import React from 'react';
import { Truck, Clock, MapPin, FileText, AlertTriangle } from 'lucide-react';
import { Card } from '../common';

const AppLayout = ({ children, currentHours = 0, maxHours = 70, complianceStatus = 'compliant', activeTab = 'planning', onTabChange }) => {
  const hoursPercentage = (currentHours / maxHours) * 100;
  
  const getStatusColor = () => {
    if (complianceStatus === 'violation') return 'text-error-600 bg-error-50';
    if (complianceStatus === 'warning') return 'text-warning-600 bg-warning-50';
    return 'text-success-600 bg-success-50';
  };

  const getStatusText = () => {
    if (complianceStatus === 'violation') return 'VIOLATION';
    if (complianceStatus === 'warning') return 'WARNING';
    return 'COMPLIANT';
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header with HOS Status */}
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* App Title */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-primary-600 rounded-lg">
                <Truck className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-neutral-900">
                  ELD Compliance System
                </h1>
                <p className="text-sm text-neutral-500">
                  Route Planning & Hours of Service
                </p>
              </div>
            </div>

            {/* HOS Status Display */}
            <div className="flex items-center space-x-6">
              {/* Current Hours */}
              <div className="text-right">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-neutral-500" />
                  <span className="text-sm text-neutral-600">Current Hours</span>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-900">
                  {currentHours.toFixed(1)}/{maxHours}
                </div>
              </div>

              {/* HOS Progress Bar */}
              <div className="w-32">
                <div className="flex justify-between text-xs text-neutral-500 mb-1">
                  <span>HOS Status</span>
                  <span>{hoursPercentage.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-neutral-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      hoursPercentage >= 100 ? 'bg-error-500' : 
                      hoursPercentage >= 85 ? 'bg-warning-500' : 
                      'bg-success-500'
                    }`}
                    style={{ width: `${Math.min(hoursPercentage, 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Compliance Badge */}
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
                {complianceStatus === 'violation' && <AlertTriangle className="w-3 h-3 inline mr-1" />}
                {getStatusText()}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <NavTab 
              icon={MapPin} 
              label="Trip Planning" 
              active={activeTab === 'planning'}
              onClick={() => onTabChange?.('planning')}
            />
            <NavTab 
              icon={FileText} 
              label="ELD Logs" 
              active={activeTab === 'logs'}
              onClick={() => onTabChange?.('logs')}
            />
            <NavTab 
              icon={Clock} 
              label="HOS Tracker" 
              active={activeTab === 'tracker'}
              onClick={() => onTabChange?.('tracker')}
            />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
};

// Navigation Tab Component
const NavTab = ({ icon: Icon, label, active = false, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
      active
        ? 'border-primary-500 text-primary-600'
        : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
    }`}
  >
    <Icon className="w-4 h-4" />
    <span>{label}</span>
  </button>
);

export default AppLayout;