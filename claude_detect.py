"""Claude Code 状态检测、窗口扫描、终端文本读取。"""
import os
import json
import glob
import logging
import time

from pywinauto import Desktop

from config import SPINNER_CHARS, state
from win32_api import get_window_title

logger = logging.getLogger("bedcode")

_windows_cache = []
_windows_cache_time = 0


def detect_claude_state(title: str) -> str:
    if not title:
        return "unknown"
    first_char = title[0] if title else ""
    if first_char in SPINNER_CHARS:
        return "thinking"
    if first_char == "✳" or "Claude" in title:
        return "idle"
    return "unknown"


def read_terminal_text(handle: int) -> str:
    try:
        from pywinauto import Application as PwaApp
        app = PwaApp(backend="uia").connect(handle=handle)
        win = app.window(handle=handle)
        for child in win.descendants():
            try:
                iface = child.iface_text
                if iface:
                    text = iface.DocumentRange.GetText(-1)
                    if text and len(text.strip()) > 10:
                        return text
            except Exception:
                pass
            try:
                val = child.legacy_properties().get("Value", "")
                if val and len(val.strip()) > 10:
                    return val
            except Exception:
                pass
        return ""
    except Exception as e:
        logger.debug(f"UIA 文本读取失败: {e}")
        return ""


def read_last_transcript_response() -> str:
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    all_jsonl = glob.glob(os.path.join(claude_dir, "**", "*.jsonl"), recursive=True)
    all_jsonl = [f for f in all_jsonl if "subagent" not in f]
    if not all_jsonl:
        return ""
    latest = max(all_jsonl, key=os.path.getmtime)
    try:
        with open(latest, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        m = d.get("message", {})
        if m.get("role") != "assistant":
            continue
        content = m.get("content", [])
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            if parts:
                return "\n".join(parts)
    return ""


def _decode_proj_dirname(d: str) -> str:
    """Decode Claude project dir name like 'j-bedcode' -> 'j:\\bedcode'."""
    parts = d.split("-")
    if len(parts) >= 2 and len(parts[0]) == 1:
        return parts[0] + ":\\" + "\\".join(parts[1:])
    return d


def _get_active_projects_detail(max_count: int = 8) -> list[dict]:
    """Return [{name, dir_name, path}, ...] for recent projects."""
    projects_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(projects_dir):
        return []
    all_jsonl = glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))
    if not all_jsonl:
        return []
    all_jsonl.sort(key=os.path.getmtime, reverse=True)
    seen, result = [], []
    for f in all_jsonl:
        proj_dir = os.path.basename(os.path.dirname(f))
        if proj_dir not in seen:
            seen.append(proj_dir)
            parts = proj_dir.split("-")
            label = parts[-1] if parts else proj_dir
            result.append({"name": label, "dir_name": proj_dir, "path": _decode_proj_dirname(proj_dir)})
            if len(result) >= max_count:
                break
    return result


def _get_active_projects(max_count: int = 10) -> list[str]:
    projects_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(projects_dir):
        return []
    all_jsonl = glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))
    if not all_jsonl:
        return []
    all_jsonl.sort(key=os.path.getmtime, reverse=True)
    seen = []
    for f in all_jsonl:
        proj_dir = os.path.basename(os.path.dirname(f))
        if proj_dir not in seen:
            seen.append(proj_dir)
            if len(seen) >= max_count:
                break
    result = []
    for d in seen:
        parts = d.split("-")
        if len(parts) >= 2 and len(parts[0]) == 1:
            label = parts[-1] if parts[-1] else d
        else:
            label = parts[-1] if parts else d
        result.append(label)
    return result


def find_claude_windows() -> list[dict]:
    global _windows_cache, _windows_cache_time
    if time.time() - _windows_cache_time < 5:
        return _windows_cache
    desktop = Desktop(backend="uia")
    results = []
    for w in desktop.windows():
        try:
            title = w.window_text()
            if "claude" in title.lower():
                st = detect_claude_state(title)
                label = state["window_labels"].get(w.handle, "")
                results.append({
                    "title": title,
                    "handle": w.handle,
                    "class": w.class_name(),
                    "state": st,
                    "label": label,
                })
        except Exception:
            continue
    order = {"idle": 0, "thinking": 1, "unknown": 2}
    results.sort(key=lambda x: (order.get(x["state"], 9), -x["handle"]))
    _windows_cache = results
    _windows_cache_time = time.time()
    return results
