"""WebSocket endpoint /api/ws (MVP spec §15)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .deps import rt

ws_router = APIRouter()


@ws_router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    hub = rt().hub
    client = hub.connect()
    sender = asyncio.create_task(_pump(ws, client))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            op = msg.get("op")
            if op == "subscribe":
                client.subscribe(msg.get("topics") or [])
            elif op == "unsubscribe":
                client.unsubscribe(msg.get("topics") or [])
            elif op == "resume":
                client.replay_since(int(msg.get("since_seq") or 0))
            elif op == "ping":
                client.send_raw({"op": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        hub.disconnect(client)


async def _pump(ws: WebSocket, client) -> None:
    try:
        while True:
            text = await client.queue.get()
            await ws.send_text(text)
    except (asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
        return
