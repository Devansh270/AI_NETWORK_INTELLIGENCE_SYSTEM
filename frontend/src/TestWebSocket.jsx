import { useWebSocket } from "./hooks/useWebSocket";
import { WS_BASE_URL } from "./services/config";
const WS_URL = `${WS_BASE_URL}/ws/metrics`;


function TestWebSocket() {
  const {
    lastMessage,
    connectionStatus,
    messageHistory,
  } = useWebSocket(WS_URL);

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