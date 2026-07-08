import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AlertsPage from './Alerts';

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('loads alerts from the backend response shape and uses skip/limit params', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        alerts: [{
          id: 1,
          created_at: '2026-07-08T10:00:00Z',
          type: 'anomaly',
          severity: 'warning',
          score: 0.91,
          message: 'Suspicious traffic spike',
        }],
        skip: 0,
        limit: 20,
      }),
    }));

    render(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText('Suspicious traffic spike')).toBeInTheDocument();
    });

    expect(fetch).toHaveBeenCalledWith('/api/alerts?skip=0&limit=20');
  });
});
