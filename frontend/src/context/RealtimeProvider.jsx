import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { API_BASE_URL, WS_BASE_URL } from '../services/config';

export const RealtimeContext = createContext(null);

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function RealtimeProvider({ children }) {
  const metricsSocket = useWebSocket(`${WS_BASE_URL}/ws/metrics`);
  const topologySocket = useWebSocket(`${WS_BASE_URL}/topology/ws`);

  const [metricsPoints, setMetricsPoints] = useState([]);
  const [packetCount, setPacketCount] = useState(0);
  const [topology, setTopology] = useState({ nodes: [], edges: [] });

  useEffect(() => {
    if (!metricsSocket.lastMessage) {
      return;
    }

    const parsed = metricsSocket.lastMessage;
    const now = Date.now();
    const newPoint = {
      ts: now,
      time: formatTime(now),
      pps: parsed.packets_per_sec ?? parsed.pps ?? 0,
      bytes: parsed.bytes_per_sec ?? parsed.bytes ?? 0,
    };

    setPacketCount((prev) => prev + 1);
    setMetricsPoints((prev) => {
      const cutoff = now - 60 * 1000;
      return [...prev.filter((point) => point.ts > cutoff), newPoint];
    });
  }, [metricsSocket.lastMessage]);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_BASE_URL}/topology`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Topology request failed: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!cancelled && data) {
          setTopology(data);
        }
      })
      .catch((error) => {
        console.warn('[realtime] failed to fetch topology fallback', error);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (topologySocket.lastMessage) {
      setTopology(topologySocket.lastMessage);
    }
  }, [topologySocket.lastMessage]);

  const value = useMemo(() => ({
    metricsConnected: metricsSocket.connected,
    metricsConnectionStatus: metricsSocket.connectionStatus,
    metricsPoints,
    packetCount,
    topology,
    topologyConnected: topologySocket.connected,
    topologyConnectionStatus: topologySocket.connectionStatus,
  }), [metricsSocket.connected, metricsSocket.connectionStatus, metricsPoints, packetCount, topology, topologySocket.connected, topologySocket.connectionStatus]);

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const context = useContext(RealtimeContext);

  if (!context) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }

  return context;
}
