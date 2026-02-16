"""REST 端点: 直接调用现有模块。"""
import asyncio
import base64
import logging
import os
import time

from fastapi import APIRouter, Response, UploadFile, File, Form
from pydantic import BaseModel

from config import state, SHELL_TIMEOUT
from win32_api import (
    capture_window_screenshot, send_keys_to_window, send_raw_keys,
    send_ctrl_c, send_ctrl_z, get_window_title,
    get_clipboard_text, set_clipboard_text,
    copy_image_to_clipboard, paste_image_to_window,
)
from claude_detect import (
    detect_claude_state, find_claude_windows, read_terminal_text,
    read_last_transcript_response,
)
from utils import _get_handle, _needs_file, _save_msg_file, _save_state, _save_labels
from monitor import _cancel_monitor

router = APIRouter()


# ── Models ──

class SendBody(BaseModel):
    text: str

class KeysBody(BaseModel):
    keys: list[str]

class TargetBody(BaseModel):
    handle: int

class ConfigBody(BaseModel):
    auto_monitor: bool | None = None
    auto_yes: bool | None = None
    screenshot_interval: int | None = None
    quiet_start: int | None = None
    quiet_end: int | None = None
    stream_mode: bool | None = None
    cwd: str | None = None

class ClipBody(BaseModel):
    text: str

class ShellBody(BaseModel):
    cmd: str

class BatchBody(BaseModel):
    messages: list[str]

class LabelBody(BaseModel):
    handle: int
    label: str


# ── Endpoints ──

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "target_handle": state.get("target_handle"),
        "auto_monitor": state.get("auto_monitor"),
        "stream_mode": state.get("stream_mode"),
        "queue_length": len(state.get("msg_queue", [])),
        "uptime": "running",
    }


@router.get("/status")
async def status():
    handle = state.get("target_handle")
    title = ""
    st = "unknown"
    if handle:
        title = await asyncio.to_thread(get_window_title, handle) or ""
        st = detect_claude_state(title) if title else "unknown"
    label = state.get("window_labels", {}).get(handle, "")
    monitor_active = bool(state.get("monitor_task") and not state["monitor_task"].done())
    passive_active = bool(state.get("passive_monitor_task") and not state["passive_monitor_task"].done())
    return {
        "handle": handle,
        "title": title,
        "label": label,
        "state": st,
        "cwd": state.get("cwd", ""),
        "auto_monitor": state.get("auto_monitor", True),
        "auto_yes": state.get("auto_yes", False),
        "stream_mode": state.get("stream_mode", False),
        "screenshot_interval": state.get("screenshot_interval", 15),
        "monitor_active": monitor_active,
        "passive_monitor_active": passive_active,
        "queue_length": len(state["msg_queue"]),
        "quiet_start": state.get("quiet_start"),
        "quiet_end": state.get("quiet_end"),
    }


@router.get("/screenshot")
async def screenshot():
    handle = await _get_handle()
    if not handle:
        return Response(status_code=404, content="No window found")
    img = await asyncio.to_thread(capture_window_screenshot, handle)
    if not img:
        return Response(status_code=500, content="Screenshot failed")
    return Response(content=img, media_type="image/png")


@router.get("/grab")
async def grab():
    handle = await _get_handle()
    if not handle:
        return {"error": "No window found"}
    text = await asyncio.to_thread(read_terminal_text, handle)
    title = await asyncio.to_thread(get_window_title, handle) or ""
    st = detect_claude_state(title)
    return {"text": text or "", "state": st, "title": title}


@router.post("/send")
async def send(body: SendBody):
    handle = await _get_handle()
    if not handle:
        return {"status": "error", "message": "No window found"}

    inject_text = body.text
    if _needs_file(body.text):
        filepath = _save_msg_file(body.text)
        inject_text = f"请阅读这个文件并按其中的指示操作 {filepath}"

    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)

    if st == "thinking":
        if len(state["msg_queue"]) >= 50:
            return {"status": "queue_full"}
        state["msg_queue"].append(inject_text)
        return {"status": "queued", "position": len(state["msg_queue"])}

    success = await asyncio.to_thread(send_keys_to_window, handle, inject_text)
    if not success:
        return {"status": "error", "message": "Send failed"}

    state["cmd_history"].append(body.text)
    return {"status": "sent"}


@router.post("/keys")
async def keys(body: KeysBody):
    handle = await _get_handle()
    if not handle:
        return {"status": "error", "message": "No window found"}
    success = await asyncio.to_thread(send_raw_keys, handle, body.keys)
    return {"status": "ok" if success else "error"}


@router.post("/break")
async def break_claude():
    handle = await _get_handle()
    if not handle:
        return {"status": "error", "message": "No window found"}
    _cancel_monitor()
    success = await asyncio.to_thread(send_ctrl_c, handle)
    return {"status": "ok" if success else "error"}


@router.post("/undo")
async def undo():
    handle = await _get_handle()
    if not handle:
        return {"status": "error", "message": "No window found"}
    success = await asyncio.to_thread(send_ctrl_z, handle)
    return {"status": "ok" if success else "error"}


@router.get("/windows")
async def windows():
    wins = await asyncio.to_thread(find_claude_windows)
    result = []
    for w in wins:
        st = detect_claude_state(w["title"])
        label = state.get("window_labels", {}).get(w["handle"], "")
        is_current = w["handle"] == state.get("target_handle")
        result.append({
            "handle": w["handle"],
            "title": w["title"],
            "state": st,
            "label": label,
            "current": is_current,
        })
    return {"windows": result}


@router.post("/target")
async def target(body: TargetBody):
    title = await asyncio.to_thread(get_window_title, body.handle)
    if not title:
        return {"status": "error", "message": "Window not found"}
    state["target_handle"] = body.handle
    st = detect_claude_state(title)
    label = state.get("window_labels", {}).get(body.handle, "")
    return {"status": "ok", "title": title, "state": st, "label": label}


@router.get("/queue")
async def queue():
    items = list(state["msg_queue"])
    return {"items": [{"index": i, "text": m} for i, m in enumerate(items)]}


@router.delete("/queue")
async def queue_clear():
    state["msg_queue"].clear()
    return {"status": "ok"}


@router.get("/history")
async def history():
    return {"items": list(state["cmd_history"])}


@router.get("/cost")
async def cost():
    from claude_detect import calc_session_cost
    info = await asyncio.to_thread(calc_session_cost)
    return info


@router.get("/export")
async def export():
    text = await asyncio.to_thread(read_last_transcript_response)
    if not text or len(text.strip()) < 10:
        return {"text": ""}
    return {"text": text}


@router.get("/clipboard")
async def clipboard_get():
    text = await asyncio.to_thread(get_clipboard_text)
    return {"text": text or ""}


@router.post("/clipboard")
async def clipboard_set(body: ClipBody):
    success = await asyncio.to_thread(set_clipboard_text, body.text)
    return {"status": "ok" if success else "error"}


@router.patch("/config")
async def config_update(body: ConfigBody):
    changed = {}
    for field in ("auto_monitor", "auto_yes", "screenshot_interval", "quiet_start", "quiet_end", "stream_mode", "cwd"):
        val = getattr(body, field, None)
        if val is not None:
            state[field] = val
            changed[field] = val
    if changed:
        _save_state()
    return {"status": "ok", "changed": changed}


@router.post("/shell")
async def shell(body: ShellBody):
    import subprocess
    from stream_mode import GIT_BASH_PATH
    DANGEROUS = {"rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){ :|:&", "> /dev/sd"}
    if any(p in body.cmd.lower() for p in DANGEROUS):
        return {"status": "error", "message": "Dangerous command blocked"}
    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(
                [GIT_BASH_PATH, "-c", body.cmd],
                capture_output=True, text=True,
                timeout=SHELL_TIMEOUT, cwd=state["cwd"],
            )
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if not output.strip():
            output = f"(exit code: {result.returncode})"
        return {"output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"Timeout ({SHELL_TIMEOUT}s)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/batch")
async def batch(body: BatchBody):
    msgs = [m.strip() for m in body.messages if m.strip()]
    if not msgs:
        return {"status": "error", "message": "No messages"}
    space = 50 - len(state["msg_queue"])
    if space <= 0:
        return {"status": "error", "message": "Queue full"}
    added = msgs[:space]
    for m in added:
        state["msg_queue"].append(m)
    return {"status": "ok", "added": len(added), "total": len(state["msg_queue"])}


@router.post("/image")
async def upload_image(file: UploadFile = File(...), caption: str = Form("")):
    logger = logging.getLogger("bedcode")
    handle = await _get_handle()
    if not handle:
        return {"status": "error", "message": "No active window"}
    img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
    os.makedirs(img_dir, exist_ok=True)
    filepath = os.path.join(img_dir, f"web_{int(time.time())}_{file.filename or 'img.png'}")
    data = await file.read()
    with open(filepath, "wb") as f:
        f.write(data)
    logger.info(f"[API/image] saved: {filepath} ({len(data)} bytes)")
    text = caption or "请分析这个图片"
    # 检查 Claude 状态
    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)
    # thinking 时无法 Alt+V，降级为路径注入排队
    if st == "thinking":
        inject_text = f"{text} {filepath}"
        if len(state["msg_queue"]) >= 50:
            return {"status": "error", "message": "Queue full"}
        state["msg_queue"].append(inject_text)
        logger.info(f"[API/image] thinking, queued path: {inject_text[:60]}")
        return {"status": "queued", "position": len(state["msg_queue"])}
    # idle 时尝试 Alt+V 粘贴
    if not state.get("stream_mode"):
        copied = await asyncio.to_thread(copy_image_to_clipboard, filepath)
        logger.info(f"[API/image] clipboard: {copied}")
        if copied:
            pasted = await asyncio.to_thread(paste_image_to_window, handle)
            logger.info(f"[API/image] paste: {pasted}")
            if pasted:
                await asyncio.sleep(2)  # 等待 Claude 处理图片粘贴
                await asyncio.to_thread(send_keys_to_window, handle, text)
                logger.info(f"[API/image] keys: {text[:50]}")
                return {"status": "sent", "method": "paste"}
    # 降级：路径注入
    inject_text = f"{text} {filepath}"
    await asyncio.to_thread(send_keys_to_window, handle, inject_text)
    logger.info(f"[API/image] fallback path: {inject_text[:60]}")
    return {"status": "sent", "method": "path"}


@router.post("/label")
async def label_set(body: LabelBody):
    state.setdefault("window_labels", {})[body.handle] = body.label
    _save_labels()
    return {"status": "ok", "handle": body.handle, "label": body.label}
