import { useState, useEffect, useRef, useCallback } from "react";

export function useTopology() {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${WS_URL}/topology/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      console.log("[topology] WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setTopology(data);
      } catch (e) {
        console.error("[topology] Parse error:", e);
      }
    };

    ws.onerror = (err) => {
      console.error("[topology] WS error:", err);
      setConnectionStatus("error");
    };

    ws.onclose = () => {
      setConnectionStatus("reconnecting");
      reconnectTimeout.current = setTimeout(connect, 3000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connect]);

  const selectNode = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node?.id ? null : node));
  }, []);

  return { topology, selectedNode, selectNode, connectionStatus };
}