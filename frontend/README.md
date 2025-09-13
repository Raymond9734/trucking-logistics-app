# Trucking Logistics App - Frontend

A comprehensive ELD compliance and route planning system for the trucking industry, built with React, Vite, and Tailwind CSS.

## 🚀 Phase 1 Implementation Complete

Phase 1 focuses on establishing a solid foundation with a professional design system and modular component architecture.

### ✅ What's Included in Phase 1:

- **Complete Design System**: Professional trucking industry color palette, typography, and spacing
- **Modular Component Architecture**: Organized folder structure with reusable components
- **Core UI Components**: Button, Input, Card, Loading components with accessibility features
- **Tailwind CSS Configuration**: Custom design tokens and utility classes
- **Development Setup**: Vite, ESLint, and modern React 19 configuration
- **OpenStreetMap Ready**: Configured for Leaflet integration in Phase 2

## 🎨 Design System

### Color Palette
- **Primary Blue**: Trust and professionalism (#3b82f6)
- **Secondary Orange**: High visibility safety color (#f97316) 
- **Status Colors**: Success, Warning, Error, Info variants
- **High Contrast Neutrals**: Excellent readability in various lighting conditions

### Key Features
- **Touch-Friendly**: Minimum 44px touch targets for gloved operation
- **Accessibility**: WCAG AA compliant with proper focus management
- **Responsive**: Mobile-first approach optimized for tablets and phones
- **Print Support**: Optimized styles for ELD log printing

## 📁 Project Structure

```
src/
├── components/
│   ├── common/           # Reusable UI components
│   │   ├── Button/       # Button component with variants
│   │   ├── Input/        # Form input with validation
│   │   ├── Card/         # Content containers
│   │   └── Loading/      # Loading states and skeletons
│   ├── forms/            # Trip input forms (Phase 2)
│   ├── maps/             # Route mapping components (Phase 2)
│   ├── logs/             # ELD log components (Phase 2)
│   └── layout/           # App layout components (Phase 2)
├── hooks/                # Custom React hooks
├── services/             # API communication layer
├── utils/                # Helper functions and utilities
├── constants/            # Design system and app constants
├── context/              # Global state management
└── styles/               # Global CSS and Tailwind config
```

## 🛠️ Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trucking-logistics-app/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to `http://localhost:5173`

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🧩 Component Usage Examples

### Button Component
```jsx
import { Button } from './components';

// Basic usage
<Button variant="primary" size="md">
  Save Trip
</Button>

// With loading state
<Button loading={isSubmitting} onClick={handleSubmit}>
  Calculate Route
</Button>

// With icons
<Button leftIcon={<MapIcon />} variant="secondary">
  View Map
</Button>
```

### Input Component
```jsx
import { Input } from './components';

// Basic input with validation
<Input
  label="Driver Name"
  required
  error={errors.driverName}
  helperText="Full legal name as appears on CDL"
  onChange={(e) => setDriverName(e.target.value)}
/>
```

### Card Component
```jsx
import { Card, CardHeader, CardTitle, CardContent } from './components';

<Card variant="hover">
  <CardHeader>
    <CardTitle>HOS Status</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Current driving time: 8.5 hours</p>
  </CardContent>
</Card>
```

## 🎯 Design Principles

### 1. Driver-First UX
- Large touch targets for gloved operation
- High contrast for various lighting conditions
- Minimal cognitive load with clear visual hierarchy
- Quick access to critical functions

### 2. Compliance-Focused
- Clear status indicators for HOS compliance
- Easy-to-read time displays and progress bars
- Prominent warnings and violation alerts
- Professional appearance suitable for DOT inspections

### 3. Mobile-Optimized
- Responsive design works on tablets and phones
- Touch-friendly interface with proper spacing
- Fast loading times for on-the-road use
- Offline capability planning for basic functions

## 🔧 Customization

### Extending the Design System

The design system is fully customizable through `src/constants/designSystem.js` and `tailwind.config.js`.

### Adding New Components

1. Create component directory in appropriate folder
2. Follow the established pattern with:
   - Component file (`.jsx`)
   - Index file for clean imports
   - Consistent prop interface with size/variant options

### Color System Usage

```css
/* Use design tokens in CSS */
.custom-element {
  @apply bg-primary-600 text-white;
  @apply hover:bg-primary-700;
  @apply focus:ring-primary-500;
}
```

```jsx
// Or use in JavaScript
import { COLORS } from '../constants/designSystem';

const customStyles = {
  backgroundColor: COLORS.primary[600],
  borderColor: COLORS.secondary[500],
};
```

## 📈 Next Phase: Core Features

### Phase 2 Will Include:
- Trip planning form with location autocomplete
- OpenStreetMap integration with route display  
- Real-time HOS compliance tracking
- ELD log sheet generation and display
- Route optimization with rest stop planning

### Phase 3 Will Add:
- Advanced animations and transitions
- Comprehensive error handling
- Offline functionality
- Performance optimizations
- Accessibility enhancements

## 🤝 Development Guidelines

### Code Style
- Use functional components with hooks
- Follow established naming conventions
- Include proper TypeScript-style prop documentation
- Maintain accessibility standards (ARIA attributes, keyboard navigation)

### Component Development
- Each component should be modular and reusable
- Include size and variant props where appropriate
- Use the `cn()` utility for class name merging
- Follow the established file structure pattern

### Performance
- Use React.memo() for expensive components
- Implement proper loading states
- Optimize images and assets
- Consider bundle splitting for large features

## 📝 Contributing

1. Follow the established component patterns
2. Update documentation for new features
3. Test components in different browsers
4. Ensure mobile responsiveness
5. Maintain accessibility standards

## 🐛 Troubleshooting

### Common Issues

**Tailwind classes not working:**
- Ensure PostCSS is configured correctly
- Check that Tailwind directives are imported in `index.css`
- Verify content paths in `tailwind.config.js`

**Component imports failing:**
- Check that index files are properly configured
- Ensure consistent export/import patterns
- Use absolute imports from `src/components`

## 📄 License

This project is part of a full-stack development assessment for trucking logistics management.

---

**Status**: Phase 1 Complete ✅  
**Next**: Phase 2 - Core Features Implementation  
**Timeline**: 16 hours total development time
