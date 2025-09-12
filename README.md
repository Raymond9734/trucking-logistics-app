# Trucking Logistics App

A comprehensive Electronic Logging Device (ELD) compliance and route planning application for commercial truck drivers, ensuring adherence to Federal Motor Carrier Safety Administration (FMCSA) Hours of Service (HOS) regulations.

## 📋 Project Overview

This application helps truck drivers plan compliant routes by automatically calculating mandatory rest stops, generating ELD daily log sheets, and ensuring trips comply with federal trucking regulations. The system prevents costly violations and promotes road safety by enforcing HOS limits.

### 🎯 Problem Statement

- Truck drivers face complex federal HOS regulations with severe penalties for violations
- Manual calculation of compliance requirements is error-prone and time-consuming
- Current tools lack integration between route planning and regulatory compliance
- ELD log generation is often manual and inefficient

### 💡 Solution

An integrated web application that combines intelligent route planning with automated ELD compliance, providing drivers with legally compliant trip plans and pre-generated documentation.

## ✨ Key Features

### 🗺️ Route Planning & Mapping

- Interactive route visualization with pickup and delivery points
- Automatic calculation of mandatory rest stops based on HOS regulations
- Integration with mapping APIs for real-time route data
- Fuel stop recommendations (every 1,000 miles maximum)

### 📊 HOS Compliance Engine

- Real-time validation against federal trucking regulations
- 11-hour daily driving limit enforcement
- 14-hour work window calculations
- 70-hour/8-day cycle tracking
- 30-minute break requirement monitoring
- 10-hour rest period validation

### 📋 ELD Log Generation

- Automated daily log sheet creation
- FMCSA-compliant formatting
- Pre-populated driver information and route details
- Multi-day trip support with sequential log sheets
- Printable and digital formats

### ⚡ Smart Notifications

- HOS violation warnings
- Optimal departure time recommendations
- Break schedule alerts
- Compliance status updates

## 🏗️ Technical Architecture

### Backend (Django REST API)

- **Framework:** Django 4.x with Django REST Framework
- **Database:** PostgreSQL (production) / SQLite (development)
- **API Design:** RESTful architecture with JSON responses
- **External Integrations:** Mapping APIs, route optimization services

### Frontend (React SPA)

- **Framework:** React 18.x with functional components and hooks
- **State Management:** React Context API / Redux (if needed)
- **Mapping:** Leaflet.js with React-Leaflet
- **Styling:** CSS Modules / Styled Components
- **HTTP Client:** Axios for API communication

## 🔄 User Flow

### 1. **Trip Planning Phase**

```md
🚚 Driver Access → 📝 Input Trip Details → ⚡ System Processing
```

- Driver accesses the web application
- Enters current location, pickup point, and delivery destination
- Provides current cycle hours (how many hours worked in past 8 days)
- Submits trip planning request

### 2. **System Processing Phase**

```md
🧮 Route Calculation → 📊 HOS Validation → 🛑 Break Calculation
```

- System calculates optimal route using mapping APIs
- Validates trip against HOS regulations (11hr daily, 70hr/8-day limits)
- Determines mandatory rest stops and break requirements
- Identifies fuel stop locations (every 1,000 miles)

### 3. **Results Display Phase**

```md
🗺️ Interactive Map → 📋 ELD Logs → ✅ Compliance Summary
```

- Displays interactive map with complete route
- Shows all mandatory stops (rest, fuel, breaks)
- Generates pre-filled ELD daily log sheets
- Provides compliance summary and warnings

### 4. **Trip Execution Phase**

```md
📄 Download Logs → 🚛 Execute Trip → ✅ Stay Compliant
```

- Driver downloads/prints ELD log sheets
- Follows planned route with mandatory stops
- Maintains compliance with federal regulations
- Avoids costly violations and penalties

## 🛠️ Core Functionality

### Input Processing

- **Location Validation:** Verify pickup/delivery addresses exist
- **Distance Calculation:** Calculate total trip mileage
- **Time Estimation:** Estimate driving time based on route and speed limits
- **Current Status:** Process driver's current HOS cycle usage

### HOS Compliance Engine

- **Daily Limits:** Enforce 11-hour driving and 14-hour work window limits
- **Weekly Limits:** Track 70-hour/8-day cycle compliance
- **Break Requirements:** Calculate 30-minute and 10-hour rest requirements
- **Violation Prevention:** Alert drivers to potential compliance issues

### Route Optimization

- **Efficient Routing:** Find optimal path considering HOS constraints
- **Rest Stop Placement:** Position mandatory breaks at appropriate locations
- **Fuel Planning:** Schedule fuel stops within regulatory requirements
- **Time Management:** Optimize departure times for compliance

### ELD Generation

- **Automated Creation:** Generate compliant daily log sheets
- **Multi-day Support:** Create sequential logs for longer trips
- **FMCSA Formatting:** Ensure logs meet federal standards
- **Digital/Print Options:** Provide multiple output formats

## 🌟 Expected Outcomes

### For Drivers

- ✅ **Compliance Assurance:** Eliminate risk of HOS violations
- ⏱️ **Time Savings:** Reduce manual calculation time by 90%
- 💰 **Cost Avoidance:** Prevent expensive fines and penalties
- 📈 **Efficiency:** Optimize routes for maximum productivity

### For Fleet Operators

- 📊 **Risk Reduction:** Minimize liability from driver violations
- 💼 **Operational Excellence:** Improve fleet compliance rates
- 📋 **Documentation:** Automated ELD record keeping
- 🎯 **Performance:** Enhanced route planning capabilities
