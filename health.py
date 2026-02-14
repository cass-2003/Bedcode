"""Minimal health-check HTTP endpoint."""
import os, time, asyncio, json
from config import state, logger

_START = time.time()


async def _handle(reader, writer):
    await reader.read(1024)
    body = json.dumps({
        "status": "ok",
        "target_handle": state.get("target_handle"),
        "auto_monitor": state.get("auto_monitor"),
        "stream_mode": state.get("stream_mode"),
        "queue_length": len(state.get("msg_queue", [])),
        "session_costs": state.get("session_costs", {}),
        "uptime_seconds": round(time.time() - _START, 1),
    })
    resp = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"\r\n{body}"
    )
    writer.write(resp.encode())
    await writer.drain()
    writer.close()


async def start_health_server():
    port = int(os.environ.get("HEALTH_PORT", "8099"))
    srv = await asyncio.start_server(_handle, "0.0.0.0", port)
    state["_health_server"] = srv
    logger.info(f"Health endpoint on :{port}")
