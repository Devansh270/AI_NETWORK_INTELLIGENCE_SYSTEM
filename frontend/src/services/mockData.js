export const mockTopology = {
  nodes: [
    { id: 'h1', label: 'h1', type: 'host', ip: '10.0.0.1' },
    { id: 'h2', label: 'h2', type: 'host', ip: '10.0.0.2' },
    { id: 'h3', label: 'h3', type: 'host', ip: '10.0.0.3' },
    { id: 's1', label: 's1', type: 'switch', ip: '' },
  ],
  edges: [
    { id: 'h1-s1', source: 'h1', target: 's1', bw_mbps: 10, utilization: 0.24 },
    { id: 'h2-s1', source: 'h2', target: 's1', bw_mbps: 10, utilization: 0.55 },
    { id: 'h3-s1', source: 'h3', target: 's1', bw_mbps: 10, utilization: 0.81 },
  ],
};

export const mockAlerts = [
  {
    id: 'mock-alert-1',
    created_at: '2026-07-08T10:00:00Z',
    type: 'anomaly',
    severity: 'warning',
    score: 0.91,
    message: 'Suspicious traffic spike detected on the edge link.',
  },
  {
    id: 'mock-alert-2',
    created_at: '2026-07-08T10:05:00Z',
    type: 'policy',
    severity: 'info',
    score: 0.42,
    message: 'Routing policy rebalanced successfully.',
  },
];

export const mockMetricsMessage = {
  packets_per_sec: 128,
  bytes_per_sec: 18240,
  protocols: {
    TCP: 45,
    UDP: 35,
    ICMP: 12,
    OTHER: 8,
  },
};

export function shouldUseMockData() {
  if (typeof window === 'undefined') {
    return false;
  }

  const params = new URLSearchParams(window.location.search);
  
  // Default to mock mode in development
  const isDev = import.meta.env.DEV;
  const useMock = (
    isDev ||
    import.meta.env.VITE_USE_MOCKS === 'true' ||
    params.get('mock') === '1' ||
    params.get('mock') === 'true'
  );
  
  if (useMock) {
    console.log("[mockData] Mock mode is ENABLED");
  }
  
  return useMock;
}

export function createMockMetricsStream(onMessage) {
  let tick = 0;
  const timer = window.setInterval(() => {
    tick += 1;
    onMessage({
      ...mockMetricsMessage,
      packets_per_sec: mockMetricsMessage.packets_per_sec + tick * 7,
      bytes_per_sec: mockMetricsMessage.bytes_per_sec + tick * 300,
      protocols: {
        TCP: 45 + Math.floor(Math.random() * 10),
        UDP: 35 + Math.floor(Math.random() * 10),
        ICMP: 12 + Math.floor(Math.random() * 5),
        OTHER: 8 + Math.floor(Math.random() * 3),
      },
    });
  }, 1200);

  return () => window.clearInterval(timer);
}

export function createMockTopologyStream(onMessage) {
  let tick = 0;
  const timer = window.setInterval(() => {
    tick += 1;
    const edges = mockTopology.edges.map((edge, index) => ({
      ...edge,
      utilization: Math.min(0.95, Math.max(0.1, edge.utilization + (index === 1 ? 0.04 : -0.02) + tick * 0.001)),
    }));
    onMessage({ ...mockTopology, edges });
  }, 3000);

  return () => window.clearInterval(timer);
}
