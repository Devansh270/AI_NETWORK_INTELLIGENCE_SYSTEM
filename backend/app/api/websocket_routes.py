from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import redis.asyncio as redis

from app.websocket.manager import ConnectionManager

# One shared ConnectionManager instance
manager = ConnectionManager()

# WebSocket router
router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)


@router.websocket("/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint that listens to Redis 'packets' channel
    and broadcasts packet events to all connected clients.
    """
    await manager.connect(websocket)

    pubsub = None

    try:
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379")

        # Subscribe to packets channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("packets")

        # Listen forever for Redis messages
        async for message in pubsub.listen():

            # Skip subscribe/unsubscribe notifications
            if message["type"] != "message":
                continue

            data = message["data"]

            # Redis often returns bytes
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            # Broadcast to all connected WebSocket clients
            await manager.broadcast(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    finally:
        manager.disconnect(websocket)

        if pubsub:
            await pubsub.close()