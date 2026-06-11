import { useWebSocket } from "./hooks/useWebSocket";

function TestWebSocket() {
  const {
    lastMessage,
    connectionStatus,
    messageHistory,
  } = useWebSocket("ws://127.0.0.1:8000/ws/metrics");

  return (
    <div style={{ padding: "20px" }}>
      <h1>WebSocket Test</h1>

      <h2>Status: {connectionStatus}</h2>

      <h3>Latest Message:</h3>

      <pre>
        {lastMessage
          ? JSON.stringify(lastMessage, null, 2)
          : "No messages yet"}
      </pre>

      <h3>Total Messages Stored:</h3>

      <p>{messageHistory.length}</p>
    </div>
  );
}

export default TestWebSocket;