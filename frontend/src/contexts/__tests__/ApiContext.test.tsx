import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ApiProvider, useApi } from '../ApiContext';
import { MockApiService } from '../../services/MockApiService';

// A dummy component to test useApi inside Provider
const DummyConsumer: React.FC = () => {
  const api = useApi();
  const isMock = api instanceof MockApiService;
  return (
    <div>
      <span data-testid="is-mock">{isMock ? 'YES' : 'NO'}</span>
    </div>
  );
};

describe('ApiContext & useApi', () => {
  it('should successfully provide ApiService to child components', () => {
    render(
      <ApiProvider>
        <DummyConsumer />
      </ApiProvider>
    );

    // By default, it should use FastApiService if no env variables say otherwise
    expect(screen.getByTestId('is-mock')).toHaveTextContent('NO');
  });

  it('should accept a service override for test injections', () => {
    const customMockService = new MockApiService();
    
    render(
      <ApiProvider serviceOverride={customMockService}>
        <DummyConsumer />
      </ApiProvider>
    );

    expect(screen.getByTestId('is-mock')).toHaveTextContent('YES');
  });

  it('should throw an error if useApi is used outside ApiProvider', () => {
    // Suppress console.error in vitest output for expected React boundary error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<DummyConsumer />);
    }).toThrow('useApi must be used within an ApiProvider');

    spy.mockRestore();
  });
});
