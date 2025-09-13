/**
 * Application Context
 * 
 * Global state management for the trucking logistics application.
 * This will be expanded in Phase 2 with specific app state.
 */

import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Initial application state
const initialState = {
  // User and authentication
  user: null,
  isAuthenticated: false,
  
  // Current trip state (to be implemented in Phase 2)
  currentTrip: null,
  
  // HOS compliance state (to be implemented in Phase 2)
  hosStatus: {
    drivingHours: 0,
    onDutyHours: 0,
    weeklyHours: 0,
    lastBreak: null,
    complianceStatus: 'compliant', // 'compliant' | 'warning' | 'violation'
  },
  
  // UI state
  ui: {
    sidebarOpen: false,
    loading: false,
    notifications: [],
    theme: 'light', // 'light' | 'dark' | 'auto'
  },
  
  // Application settings
  settings: {
    units: 'imperial', // 'imperial' | 'metric'
    timeZone: 'America/New_York',
    autoSave: true,
    soundNotifications: true,
  },
};

// Action types
const ActionTypes = {
  // Authentication
  SET_USER: 'SET_USER',
  SET_AUTHENTICATED: 'SET_AUTHENTICATED',
  LOGOUT: 'LOGOUT',
  
  // Trip management (Phase 2)
  SET_CURRENT_TRIP: 'SET_CURRENT_TRIP',
  UPDATE_TRIP_STATUS: 'UPDATE_TRIP_STATUS',
  
  // HOS compliance (Phase 2)
  UPDATE_HOS_STATUS: 'UPDATE_HOS_STATUS',
  RESET_HOS_TIMER: 'RESET_HOS_TIMER',
  
  // UI state
  TOGGLE_SIDEBAR: 'TOGGLE_SIDEBAR',
  SET_LOADING: 'SET_LOADING',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  SET_THEME: 'SET_THEME',
  
  // Settings
  UPDATE_SETTINGS: 'UPDATE_SETTINGS',
};

// Reducer function
function appReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload,
      };
      
    case ActionTypes.SET_AUTHENTICATED:
      return {
        ...state,
        isAuthenticated: action.payload,
      };
      
    case ActionTypes.LOGOUT:
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        currentTrip: null,
      };
      
    case ActionTypes.SET_CURRENT_TRIP:
      return {
        ...state,
        currentTrip: action.payload,
      };
      
    case ActionTypes.UPDATE_HOS_STATUS:
      return {
        ...state,
        hosStatus: {
          ...state.hosStatus,
          ...action.payload,
        },
      };
      
    case ActionTypes.TOGGLE_SIDEBAR:
      return {
        ...state,
        ui: {
          ...state.ui,
          sidebarOpen: !state.ui.sidebarOpen,
        },
      };
      
    case ActionTypes.SET_LOADING:
      return {
        ...state,
        ui: {
          ...state.ui,
          loading: action.payload,
        },
      };
      
    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        ui: {
          ...state.ui,
          notifications: [...state.ui.notifications, action.payload],
        },
      };
      
    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        ui: {
          ...state.ui,
          notifications: state.ui.notifications.filter(
            notification => notification.id !== action.payload
          ),
        },
      };
      
    case ActionTypes.SET_THEME:
      return {
        ...state,
        ui: {
          ...state.ui,
          theme: action.payload,
        },
      };
      
    case ActionTypes.UPDATE_SETTINGS:
      return {
        ...state,
        settings: {
          ...state.settings,
          ...action.payload,
        },
      };
      
    default:
      return state;
  }
}

// Create contexts
const AppStateContext = createContext();
const AppDispatchContext = createContext();

// Context provider component
export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

// Custom hooks for accessing context
export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error('useAppState must be used within an AppProvider');
  }
  return context;
}

export function useAppDispatch() {
  const context = useContext(AppDispatchContext);
  if (!context) {
    throw new Error('useAppDispatch must be used within an AppProvider');
  }
  return context;
}

// Custom hook for accessing both state and dispatch
export function useApp() {
  return {
    state: useAppState(),
    dispatch: useAppDispatch(),
  };
}

// Action creators
export const AppActions = {
  // Authentication actions
  setUser: (user) => ({ type: ActionTypes.SET_USER, payload: user }),
  setAuthenticated: (isAuthenticated) => ({ 
    type: ActionTypes.SET_AUTHENTICATED, 
    payload: isAuthenticated 
  }),
  logout: () => ({ type: ActionTypes.LOGOUT }),
  
  // Trip management actions (Phase 2)
  setCurrentTrip: (trip) => ({ type: ActionTypes.SET_CURRENT_TRIP, payload: trip }),
  
  // HOS compliance actions (Phase 2)
  updateHOSStatus: (status) => ({ type: ActionTypes.UPDATE_HOS_STATUS, payload: status }),
  
  // UI actions
  toggleSidebar: () => ({ type: ActionTypes.TOGGLE_SIDEBAR }),
  setLoading: (loading) => ({ type: ActionTypes.SET_LOADING, payload: loading }),
  addNotification: (notification) => ({ 
    type: ActionTypes.ADD_NOTIFICATION, 
    payload: {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      ...notification,
    }
  }),
  removeNotification: (id) => ({ 
    type: ActionTypes.REMOVE_NOTIFICATION, 
    payload: id 
  }),
  setTheme: (theme) => ({ type: ActionTypes.SET_THEME, payload: theme }),
  
  // Settings actions
  updateSettings: (settings) => ({ 
    type: ActionTypes.UPDATE_SETTINGS, 
    payload: settings 
  }),
};

// Higher-order component for consuming context
export function withAppContext(Component) {
  return function ComponentWithAppContext(props) {
    const appContext = useApp();
    return <Component {...props} app={appContext} />;
  };
}

export { ActionTypes };
