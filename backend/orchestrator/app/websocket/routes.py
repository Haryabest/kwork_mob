"""WebSocket: очередь для пользователей и воркеров."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter()


@ws_router.websocket("/ws/queue/{user_id}")
async def queue_ws(websocket: WebSocket, user_id: int):
    """WebSocket для обновлений очереди (EWT, статус заказа)."""
    await websocket.accept()
    try:
        while True:
            # TODO: подписка на Redis Pub/Sub
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "user_id": user_id})
    except WebSocketDisconnect:
        pass


@ws_router.websocket("/ws/worker")
async def worker_ws(websocket: WebSocket):
    """WebSocket для воркеров: регистрация, задачи, heartbeat."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # TODO: обработка ready, heartbeat, task_completed и т.д.
            await websocket.send_json({"type": "ack"})
    except WebSocketDisconnect:
        pass
