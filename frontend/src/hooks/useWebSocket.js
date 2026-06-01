import { useEffect, useRef, useState } from "react";

export function useWebSocket(url) {
  // stores latest received message
  const [lastMessage, setLastMessage] = useState(null);

  // tracks websocket connection status
  const [connectionStatus, setConnectionStatus] =
    useState("connecting");

  // stores last 60 messages
  const [messageHistory, setMessageHistory] = useState([]);

  // stores websocket instance
  const wsRef = useRef(null);

  useEffect(() => {
    // create websocket connection
    const ws = new WebSocket(url);

    // store websocket in ref
    wsRef.current = ws;

    // websocket connected
    ws.onopen = () => {
      console.log("WebSocket connected");
      setConnectionStatus("connected");
    };

    // websocket error
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnectionStatus("disconnected");
    };

    // websocket closed
    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setConnectionStatus("disconnected");
    };

    // receive message
    ws.onmessage = (event) => {
      try {
        // parse incoming JSON
        const data = JSON.parse(event.data);

        // update latest message
        setLastMessage(data);

        // keep only latest 60 messages
        setMessageHistory((prev) => [
          ...prev.slice(-59),
          data,
        ]);
      } catch (error) {
        console.warn(
          "WebSocket message parse error:",
          event.data
        );
      }
    };

    // cleanup function
    return () => {
      console.log("Closing WebSocket connection");

      ws.close();
    };
  }, [url]);

  // return hook values
  return {
    lastMessage,
    connectionStatus,
    messageHistory,
  };
}