"""工具函数: 文本分割、结果发送、文件保存、路径持久化。"""
import os
import json
import re
import time
import html
import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton
from telegram.ext import ContextTypes

from config import state, LABELS_FILE, RECENT_DIRS_FILE, TEMPLATES_FILE, PANEL_FILE, ALIASES_FILE, STATE_FILE
from win32_api import get_window_title
from claude_detect import find_claude_windows

logger = logging.getLogger("bedcode")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(_BASE_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)
MSG_DIR = os.path.join(_BASE_DIR, "messages")
os.makedirs(MSG_DIR, exist_ok=True)

_UNSAFE_CHARS = set('{}"$\\')


def split_text(text: str, max_len: int = 3500) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        idx = text.rfind("\n", 0, max_len)
        if idx == -1:
            idx = max_len
        chunks.append(text[:idx])
        text = text[idx:].lstrip("\n")
    return chunks


def _md_table_to_text(text: str) -> str:
    """Convert markdown tables to plain text for Telegram display."""
    lines = text.split("\n")
    result = []
    table_lines = []

    def _flush_table():
        if not table_lines:
            return
        # Parse rows
        rows = []
        for tl in table_lines:
            cells = [c.strip() for c in tl.strip().strip("|").split("|")]
            rows.append(cells)
        # Remove separator row (---|----|---)
        rows = [r for r in rows if not all(re.match(r'^[-:]+$', c) for c in r)]
        if not rows:
            return
        # Calculate column widths
        ncols = max(len(r) for r in rows)
        widths = [0] * ncols
        for r in rows:
            for i, c in enumerate(r):
                if i < ncols:
                    widths[i] = max(widths[i], len(c))
        # Format
        for i, r in enumerate(rows):
            parts = []
            for j in range(ncols):
                cell = r[j] if j < len(r) else ""
                parts.append(cell.ljust(widths[j]))
            result.append("  ".join(parts).rstrip())
            if i == 0:
                result.append("  ".join("-" * w for w in widths))

    for line in lines:
        if "|" in line and line.strip().startswith("|"):
            table_lines.append(line)
        else:
            _flush_table()
            table_lines = []
            result.append(line)
    _flush_table()
    return "\n".join(result)


async def send_result(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not text.strip():
        text = "(空输出)"
    text = _md_table_to_text(text)
    chunks = split_text(text)
    for i, chunk in enumerate(chunks):
        md_prefix = f"**[{i+1}/{len(chunks)}]**\n" if len(chunks) > 1 else ""
        html_prefix = f"<b>[{i+1}/{len(chunks)}]</b>\n" if len(chunks) > 1 else ""
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=f"{md_prefix}{chunk}", parse_mode="Markdown",
            )
        except Exception:
            safe = html.escape(chunk)
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=f"{html_prefix}<pre>{safe}</pre>", parse_mode="HTML",
                )
            except Exception:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"{html_prefix}{chunk}")
                except Exception:
                    pass


async def _get_handle() -> int | None:
    handle = state["target_handle"]
    if handle:
        title = await asyncio.to_thread(get_window_title, handle)
        if title:
            return handle
        state["target_handle"] = None
    windows = await asyncio.to_thread(find_claude_windows)
    if windows:
        state["target_handle"] = windows[0]["handle"]
        return windows[0]["handle"]
    return None


def _load_labels() -> dict:
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"加载标签失败: {e}")
    return {}


def _save_labels():
    try:
        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in state["window_labels"].items()}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存标签失败: {e}")


def _load_aliases() -> dict:
    if os.path.exists(ALIASES_FILE):
        try:
            with open(ALIASES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"加载别名失败: {e}")
    return {}


def _save_aliases():
    try:
        with open(ALIASES_FILE, "w", encoding="utf-8") as f:
            json.dump(state["aliases"], f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存别名失败: {e}")


def _load_templates() -> dict:
    if os.path.exists(TEMPLATES_FILE):
        try:
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"加载模板失败: {e}")
    return {}


def _save_templates():
    try:
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(state["templates"], f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存模板失败: {e}")


def _load_panel() -> list[list[str]] | None:
    if os.path.exists(PANEL_FILE):
        try:
            with open(PANEL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"加载面板失败: {e}")
    return None


def _save_panel(rows):
    try:
        with open(PANEL_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存面板失败: {e}")


def _load_recent_dirs() -> list[str]:
    if os.path.exists(RECENT_DIRS_FILE):
        try:
            with open(RECENT_DIRS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"加载路径历史失败: {e}")
    return []


def _save_recent_dir(path: str):
    dirs = _load_recent_dirs()
    path = os.path.normpath(path)
    dirs = [d for d in dirs if os.path.normpath(d) != path]
    dirs.insert(0, path)
    dirs = dirs[:8]
    try:
        with open(RECENT_DIRS_FILE, "w", encoding="utf-8") as f:
            json.dump(dirs, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存路径历史失败: {e}")


def _build_dir_buttons() -> list[list]:
    home = str(Path.home())
    buttons = [
        [InlineKeyboardButton(f"📂 当前: {state['cwd'][:30]}", callback_data="newdir:cwd")],
    ]
    seen = {os.path.normpath(state["cwd"])}
    if os.path.normpath(home) not in seen:
        buttons.append([InlineKeyboardButton(f"📂 {home[:30]}", callback_data=f"newdir:{home[:57]}")])
        seen.add(os.path.normpath(home))
    for d in _load_recent_dirs():
        if os.path.normpath(d) not in seen and os.path.isdir(d):
            short = os.path.basename(d) or d[:30]
            buttons.append([InlineKeyboardButton(f"📂 {short}", callback_data=f"newdir:{d[:57]}")])
            seen.add(os.path.normpath(d))
            if len(buttons) >= 6:
                break
    buttons.append([InlineKeyboardButton("✏️ 手动输入路径", callback_data="newdir:manual")])
    return buttons


def _needs_file(text: str) -> bool:
    if len(text) > 200:
        return True
    return bool(_UNSAFE_CHARS & set(text))


def _save_msg_file(text: str) -> str:
    ts = int(time.time())
    filepath = os.path.join(MSG_DIR, f"msg_{ts}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return filepath


def _save_state():
    """Persist selected state fields to disk."""
    data = {
        "session_costs": {str(k): v for k, v in state.get("session_costs", {}).items()},
        "auto_monitor": state.get("auto_monitor", True),
        "auto_yes": state.get("auto_yes", False),
        "auto_pin": state.get("auto_pin", True),
        "quiet_start": state.get("quiet_start"),
        "quiet_end": state.get("quiet_end"),
        "screenshot_interval": state.get("screenshot_interval", 15),
        "cwd": state.get("cwd", ""),
        "chat_id": state.get("chat_id"),
        "stream_mode": state.get("stream_mode", False),
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存状态失败: {e}")


def _load_state():
    """Restore state from disk."""
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        costs = data.get("session_costs", {})
        state["session_costs"] = {int(k): v for k, v in costs.items()}
        for key in ("auto_monitor", "auto_yes", "auto_pin", "stream_mode"):
            if key in data:
                state[key] = data[key]
        for key in ("quiet_start", "quiet_end", "screenshot_interval", "cwd", "chat_id"):
            if key in data and data[key] is not None:
                state[key] = data[key]
    except Exception as e:
        logger.warning(f"加载状态失败: {e}")
