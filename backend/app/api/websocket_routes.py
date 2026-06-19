import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from app.websocket.manager import ConnectionManager
from app.core.config import get_settings

logger = logging.getLogger("ainis.ws")

# One shared ConnectionManager instance
manager = ConnectionManager()

# WebSocket router
router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)


@router.websocket("/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint that listens to Redis 'packets' channel
    and broadcasts packet events to all connected clients.
    """
    await manager.connect(websocket)
    pubsub = None
    redis_client = None
    try:
        settings = get_settings()
        redis_client = redis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            decode_responses=True,
        )
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("packets")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message is None:
                continue
            if message["type"] != "message":
                continue
            await manager.broadcast(message["data"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"metrics ws ended: {e}")
    finally:
        manager.disconnect(websocket)
        if pubsub:
            await pubsub.close()
        if redis_client:
            await redis_client.aclose()


@router.websocket("/predictions")
async def websocket_predictions(websocket: WebSocket):
    """
    WebSocket endpoint that listens to Redis 'predictions' channel
    and broadcasts ML predictions (congestion + anomaly) to dashboard clients.
    """
    await websocket.accept()
    settings = get_settings()
    redis_client = redis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        decode_responses=True,
    )
    pubsub = redis_client.pubsub()
    try:
        await pubsub.subscribe("predictions")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message is None:
                continue
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"predictions ws ended: {e}")
    finally:
        try:
            await pubsub.unsubscribe("predictions")
            await pubsub.close()
        except Exception:
            pass
        try:
            await redis_client.aclose()
        except Exception:
            pass