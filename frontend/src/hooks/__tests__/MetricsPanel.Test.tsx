import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MetricsPanel from '../../components/MetricsPanel'

// Mock useWebSocket
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    lastMessage: null,
  }),
}))

// Mock Recharts
vi.mock('recharts', () => ({
  LineChart: ({ children }: any) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: any) => (
    <div>{children}</div>
  ),
}))

describe('MetricsPanel', () => {
  it('renders without crashing', () => {
    render(<MetricsPanel />)
    expect(true).toBe(true)
  })

  it('renders chart container', () => {
    const { getByTestId } = render(<MetricsPanel />)
    expect(getByTestId('line-chart')).toBeDefined()
  })

  it('handles empty websocket data', () => {
    render(<MetricsPanel />)
    expect(true).toBe(true)
  })
})