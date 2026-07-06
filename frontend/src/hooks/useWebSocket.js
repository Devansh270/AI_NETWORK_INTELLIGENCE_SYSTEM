import { useEffect, useRef, useState } from "react";

export function useWebSocket(path) {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    // CHANGED THIS LINE
    const url = path;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cancelled) {
        ws.close();
        return;
      }
      console.log("WebSocket connected");
      setConnected(true);
    };

    ws.onmessage = (event) => {
      if (!cancelled) setData(JSON.parse(event.data));
    };

    ws.onclose = () => {
      if (!cancelled) console.log("WebSocket disconnected");
      setConnected(false);
    };

    ws.onerror = (e) => {
      if (!cancelled) console.log("WebSocket error:", e);
    };

    return () => {
      cancelled = true;
      console.log("Closing WebSocket connection");

      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.addEventListener("open", () => ws.close());
      }
    };
  }, [path]);

  return { data, connected };
}