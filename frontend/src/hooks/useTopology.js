import { useState, useEffect, useRef, useCallback } from "react";
import { WS_BASE_URL } from "../services/config";

export function useTopology() {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting");

  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    let cancelled = false;

    const ws = new WebSocket(`${WS_BASE_URL}/topology/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cancelled) {
        ws.close();
        return;
      }

      setConnectionStatus("connected");
      console.log("[topology] WebSocket connected");
    };

    ws.onmessage = (event) => {
  console.log("[topology] raw:", event.data);

  if (cancelled) return;

  try {
    const data = JSON.parse(event.data);
    console.log("[topology] parsed:", data);
    setTopology(data);
  } catch (e) {
    console.error("[topology] Parse error:", e);
  }
};

    ws.onerror = (err) => {
      if (cancelled) return;

      console.error("[topology] WS error:", err);
      setConnectionStatus("error");
    };

    ws.onclose = () => {
      if (cancelled) return;

      setConnectionStatus("reconnecting");
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    return () => {
      cancelled = true;

      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.addEventListener("open", () => ws.close());
      }
    };
  }, []);

  useEffect(() => {
    const cleanup = connect();

    return () => {
      if (cleanup) cleanup();

      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [connect]);

  const selectNode = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node?.id ? null : node));
  }, []);

  return {
    topology,
    selectedNode,
    selectNode,
    connectionStatus,
  };
}