import React, { createContext, useContext, useMemo } from 'react';
import { ApiService } from '../services/ApiService';
import { MockApiService } from '../services/MockApiService';
import { FastApiService } from '../services/FastApiService';

const ApiContext = createContext<ApiService | null>(null);

interface ApiProviderProps {
  children: React.ReactNode;
  serviceOverride?: ApiService; // Useful for custom mocks in testing
}

export const ApiProvider: React.FC<ApiProviderProps> = ({ children, serviceOverride }) => {
  const service = useMemo(() => {
    if (serviceOverride) {
      return serviceOverride;
    }

    // Default to using the real backend unless VITE_USE_MOCK_API is explicitly 'true'
    const useMock = import.meta.env.VITE_USE_MOCK_API === 'true';
    
    if (useMock) {
      console.log('App is running with Centralized Mock API Service.');
      return new MockApiService();
    } else {
      console.log('App is running with FastApiService connected to the real backend.');
      return new FastApiService();
    }
  }, [serviceOverride]);

  return <ApiContext.Provider value={service}>{children}</ApiContext.Provider>;
};

export const useApi = (): ApiService => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};
