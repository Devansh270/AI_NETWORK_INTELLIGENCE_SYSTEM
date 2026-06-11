from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Stores all active WebSocket connections
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accept a new WebSocket connection and store it.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove a disconnected WebSocket from the active list.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """
        Send a message to all connected clients.

        If a client has disconnected, remove it and continue
        sending to the remaining clients.
        """
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


# Singleton manager instance
manager = ConnectionManager()