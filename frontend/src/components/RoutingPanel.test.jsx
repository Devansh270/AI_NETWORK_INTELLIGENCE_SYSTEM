import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RoutingPanel from './RoutingPanel';

beforeEach(() => {
  global.fetch = vi.fn();
});

describe('RoutingPanel', () => {
  it('renders the list of existing rules', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, name: 'prioritize-https', priority: 1 }],
    });

    render(<RoutingPanel />);

    await waitFor(() =>
      expect(screen.getByText('prioritize-https')).toBeInTheDocument()
    );
  });

  it('submits a new rule via the form', async () => {
    global.fetch
  .mockResolvedValueOnce({ ok: true, json: async () => [] }) // initial GET
  .mockResolvedValueOnce({ ok: true, json: async () => ({}) }) // POST
  .mockResolvedValueOnce({ ok: true, json: async () => [] }); // refresh GET

    render(<RoutingPanel />);

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1)
    );

    fireEvent.click(
      screen.getByRole('button', { name: /\+ new rule/i })
    );

    fireEvent.change(
      screen.getByPlaceholderText(/rule name/i),
      { target: { value: 'new-rule' } }
    );

    fireEvent.click(
      screen.getByRole('button', { name: /save rule/i })
    );

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(2)
    );

    expect(global.fetch).toHaveBeenCalledWith(
  expect.stringContaining('/routing-rules'),
  expect.objectContaining({ method: 'POST' })
);
  });

  it('shows a validation message if name is empty on submit', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    render(<RoutingPanel />);

    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledTimes(1)
    );

    fireEvent.click(
      screen.getByRole('button', { name: /\+ new rule/i })
    );

    fireEvent.click(
      screen.getByRole('button', { name: /save rule/i })
    );

    window.alert = vi.fn();

fireEvent.click(
  screen.getByRole('button', { name: /save rule/i })
);

expect(window.alert).toHaveBeenCalledWith(
  "Rule name is required"
);
  });
});