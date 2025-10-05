
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis import redis_client
import asyncio

router = APIRouter()

@router.websocket("/ws/status/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"job:{job_id}")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message['data'])
            await asyncio.sleep(0.1) # prevent busy-waiting
    except WebSocketDisconnect:
        print(f"WebSocket for job {job_id} disconnected")
    finally:
        await pubsub.unsubscribe(f"job:{job_id}")