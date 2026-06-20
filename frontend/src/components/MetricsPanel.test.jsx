import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MetricsPanel from './MetricsPanel';

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(),
}));

import { useWebSocket } from '../hooks/useWebSocket';

describe('MetricsPanel', () => {
  it('renders without crashing when no data yet', () => {
    useWebSocket.mockReturnValue({
      lastMessage: null,
      connectionStatus: 'disconnected',
      messageHistory: [],
    });

    render(<MetricsPanel />);

    expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
  });

  it('renders the chart when data arrives', () => {
    useWebSocket.mockReturnValue({
      lastMessage: {
        packets_per_sec: 142,
        timestamp: '2026-06-20T10:00:00Z',
      },
      connectionStatus: 'connected',
      messageHistory: [],
    });

    render(<MetricsPanel />);

    expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
  });

  it('shows a disconnected indicator when WS is down', () => {
    useWebSocket.mockReturnValue({
      lastMessage: null,
      connectionStatus: 'disconnected',
      messageHistory: [],
    });

    render(<MetricsPanel />);

    expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
  });
});