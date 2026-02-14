"""WebSocket 端点: 订阅 EventBus 实时推送。"""
import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.app import API_TOKEN
from core.events import bus

logger = logging.getLogger("bedcode")
router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # auth: 第一条消息必须是 {"token": "..."}
    try:
        auth = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except Exception:
        await ws.close(4001, "Auth timeout")
        return
    if auth.get("token") != API_TOKEN:
        await ws.close(4001, "Unauthorized")
        return

    queue = bus.subscribe()
    logger.info("[WS] 客户端已连接")

    async def sender():
        while True:
            event = await queue.get()
            payload = {"type": event.type, **event.data}
            if "image_bytes" in payload:
                payload["image_base64"] = base64.b64encode(payload.pop("image_bytes")).decode()
            await ws.send_json(payload)

    async def receiver():
        while True:
            try:
                msg = await ws.receive_json()
                # 客户端可通过 WS 发送命令（未来扩展）
                action = msg.get("action")
                if action == "ping":
                    await ws.send_json({"type": "pong"})
            except WebSocketDisconnect:
                raise
            except Exception:
                pass

    try:
        await asyncio.gather(sender(), receiver())
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        bus.unsubscribe(queue)
        logger.info("[WS] 客户端已断开")
