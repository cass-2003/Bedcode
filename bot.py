#!/usr/bin/env python3
"""
BedCode v5 — Telegram Bot 远程操控 Claude Code
无干扰截屏 + 终端状态监控 + SendInput 按键注入
"""

import os
import io
import html
import json
import asyncio
import subprocess
import logging
import time
import ctypes
import ctypes.wintypes
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    Update, BotCommand,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest
from pywinauto import Desktop
from PIL import Image

# ── 加载配置 ─────────────────────────────────────────────────────
load_dotenv()

# 绕过代理直连 Telegram API（避免 httpx 通过不稳定代理 TLS 握手失败）
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS = set()
for uid in os.environ.get("ALLOWED_USER_IDS", "").split(","):
    uid = uid.strip()
    if uid:
        try:
            ALLOWED_USERS.add(int(uid))
        except ValueError:
            print(f"警告: 无效的用户ID '{uid}'，已跳过")
SHELL_TIMEOUT = int(os.environ.get("SHELL_TIMEOUT", "120"))
WORK_DIR = os.environ.get("WORK_DIR", str(Path.home()))
SCREENSHOT_DELAY = int(os.environ.get("SCREENSHOT_DELAY", "15"))
LABELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "window_labels.json")
RECENT_DIRS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recent_dirs.json")

# ── 日志 ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Win32 常量 ────────────────────────────────────────────────────
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
PW_RENDERFULLCONTENT = 0x00000002
BI_RGB = 0
DIB_RGB_COLORS = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_BACK = 0x08
VK_SPACE = 0x20

# ── Win32 结构体 ──────────────────────────────────────────────────
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.wintypes.DWORD),
        ("biWidth", ctypes.wintypes.LONG),
        ("biHeight", ctypes.wintypes.LONG),
        ("biPlanes", ctypes.wintypes.WORD),
        ("biBitCount", ctypes.wintypes.WORD),
        ("biCompression", ctypes.wintypes.DWORD),
        ("biSizeImage", ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed", ctypes.wintypes.DWORD),
        ("biClrImportant", ctypes.wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", ctypes.wintypes.DWORD * 3),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# ── 命令菜单定义 ──────────────────────────────────────────────────
BOT_COMMANDS = [
    BotCommand("start", "显示状态和使用说明"),
    BotCommand("screenshot", "截取终端画面(不打断)"),
    BotCommand("grab", "抓取终端文本(不打断)"),
    BotCommand("key", "发送按键 如 1 2 ↑ ↓ tab esc enter"),
    BotCommand("watch", "手动开启监控循环"),
    BotCommand("stop", "停止监控循环"),
    BotCommand("delay", "设置截图间隔秒数"),
    BotCommand("auto", "开关自动监控"),
    BotCommand("windows", "扫描窗口并选择目标"),
    BotCommand("new", "启动新 Claude Code 实例"),
    BotCommand("cd", "切换 Shell 工作目录"),
]

# ── 常驻按钮面板 ─────────────────────────────────────────────────
REPLY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📷 截屏"), KeyboardButton("🪟 窗口"), KeyboardButton("🆕 新实例")],
        [KeyboardButton("👀 监控"), KeyboardButton("⏹ 停止"), KeyboardButton("🔄 状态")],
        [KeyboardButton("🔀 切换模式")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# ── Claude Code spinner 字符集 ────────────────────────────────────
SPINNER_CHARS = set("⠂⠃⠄⠆⠇⠋⠙⠸⠴⠤⠐⠈⠁⠉⠊⠒⠓⠔⠕⠖⠗⠘⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠵⠶⠷⠹⠺⠻⠼⠽⠾⠿")

# ── 全局状态 ───────────────────────────────────────────────────────
state = {
    "cwd": WORK_DIR,
    "target_handle": None,
    "auto_monitor": True,
    "screenshot_interval": SCREENSHOT_DELAY,
    "monitor_task": None,  # asyncio.Task for the monitor loop
    "msg_queue": [],       # 等待队列: [text, ...]
    "queue_chat_id": None, # 队列关联的 chat_id
    "status_msg": None,    # 当前状态消息(用于edit_text更新)
    "stream_proc": None,   # 流式模式子进程
    "stream_task": None,   # 流式读取 asyncio.Task
    "stream_mode": False,  # 是否处于流式模式
    "window_labels": {},   # handle(int) → 自定义标签(str)
    "last_screenshot_hash": None,  # 上次截图 MD5
}


def _load_labels() -> dict:
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            pass
    return {}


def _save_labels():
    try:
        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in state["window_labels"].items()}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存标签失败: {e}")


state["window_labels"] = _load_labels()


def _load_recent_dirs() -> list[str]:
    if os.path.exists(RECENT_DIRS_FILE):
        try:
            with open(RECENT_DIRS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_recent_dir(path: str):
    dirs = _load_recent_dirs()
    # 去重，最新的放前面，最多保留 8 个
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
    """生成路径选择按钮列表：当前目录 + Home + 历史路径 + 手动输入"""
    home = str(Path.home())
    buttons = [
        [InlineKeyboardButton(f"📂 当前: {state['cwd'][:30]}", callback_data="newdir:cwd")],
    ]
    # 历史路径（去掉与当前/home重复的）
    seen = {os.path.normpath(state["cwd"])}
    if os.path.normpath(home) not in seen:
        buttons.append([InlineKeyboardButton(f"📂 {home[:30]}", callback_data=f"newdir:{home}")])
        seen.add(os.path.normpath(home))
    for d in _load_recent_dirs():
        if os.path.normpath(d) not in seen and os.path.isdir(d):
            short = os.path.basename(d) or d[:30]
            buttons.append([InlineKeyboardButton(f"📂 {short}", callback_data=f"newdir:{d}")])
            seen.add(os.path.normpath(d))
            if len(buttons) >= 6:
                break
    buttons.append([InlineKeyboardButton("✏️ 手动输入路径", callback_data="newdir:manual")])
    return buttons


# ══════════════════════════════════════════════════════════════════
# PrintWindow 无干扰截屏
# ══════════════════════════════════════════════════════════════════
def capture_window_screenshot(handle: int) -> bytes | None:
    """使用 PrintWindow API 截屏 — 不需要激活窗口，不打断思考。"""
    try:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(handle, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None

        wnd_dc = user32.GetWindowDC(handle)
        if not wnd_dc:
            return None

        try:
            mem_dc = gdi32.CreateCompatibleDC(wnd_dc)
            bitmap = gdi32.CreateCompatibleBitmap(wnd_dc, width, height)
            old_bmp = gdi32.SelectObject(mem_dc, bitmap)

            result = user32.PrintWindow(handle, mem_dc, PW_RENDERFULLCONTENT)
            if not result:
                result = user32.PrintWindow(handle, mem_dc, 0)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # top-down
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB

            buf_size = width * height * 4
            buf = ctypes.create_string_buffer(buf_size)
            gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

            gdi32.SelectObject(mem_dc, old_bmp)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)

            img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)
            img = img.convert("RGB")

            # 缩放 + JPEG 压缩
            max_w = 1280
            if img.width > max_w:
                ratio = max_w / img.width
                img = img.resize((max_w, int(img.height * ratio)))

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=75)
            out.seek(0)
            return out.getvalue()
        finally:
            user32.ReleaseDC(handle, wnd_dc)
    except Exception as e:
        logger.exception(f"截屏失败: {e}")
        return None


def _image_hash(img_bytes: bytes) -> str:
    import hashlib
    return hashlib.md5(img_bytes).hexdigest()


# ══════════════════════════════════════════════════════════════════
# UIA 无干扰文本读取
# ══════════════════════════════════════════════════════════════════
def read_terminal_text(handle: int) -> str:
    """通过 UIA 读取终端文本 — 不需要激活窗口，不发送按键。"""
    try:
        from pywinauto import Application as PwaApp
        app = PwaApp(backend="uia").connect(handle=handle)
        win = app.window(handle=handle)

        # 尝试从子控件获取文本
        for child in win.descendants():
            try:
                # 检查是否有 TextPattern
                iface = child.iface_text
                if iface:
                    text = iface.DocumentRange.GetText(-1)
                    if text and len(text.strip()) > 10:
                        return text
            except Exception:
                pass
            try:
                # 尝试 legacy value
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
    """从最新的 Claude Code transcript jsonl 读取最后一条 assistant 文本回复。"""
    import glob
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    # 找所有 jsonl，取最新的
    all_jsonl = glob.glob(os.path.join(claude_dir, "**", "*.jsonl"), recursive=True)
    # 排除 subagents 目录
    all_jsonl = [f for f in all_jsonl if "subagent" not in f]
    if not all_jsonl:
        return ""
    latest = max(all_jsonl, key=os.path.getmtime)
    try:
        with open(latest, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""
    # 从后往前找最后一条 assistant 的 text 内容
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


# ══════════════════════════════════════════════════════════════════
# 窗口标题 + Claude 状态检测
# ══════════════════════════════════════════════════════════════════
def get_window_title(handle: int) -> str:
    """获取窗口标题 — 不需要激活窗口。"""
    try:
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buf, length + 1)
        return buf.value
    except Exception:
        return ""


def detect_claude_state(title: str) -> str:
    """根据窗口标题检测 Claude Code 状态。
    返回: "thinking" / "idle" / "unknown"
    """
    if not title:
        return "unknown"
    first_char = title[0] if title else ""
    if first_char in SPINNER_CHARS:
        return "thinking"
    if first_char == "✳" or "Claude" in title:
        return "idle"
    return "unknown"


# ══════════════════════════════════════════════════════════════════
# SendInput 按键注入
# ══════════════════════════════════════════════════════════════════
def _make_key_input(vk: int = 0, scan: int = 0, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def _send_vk(vk: int) -> None:
    """发送一个虚拟键按下+释放。"""
    inputs = (INPUT * 2)(
        _make_key_input(vk=vk),
        _make_key_input(vk=vk, flags=KEYEVENTF_KEYUP),
    )
    user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _send_unicode_char(char: str) -> None:
    """通过 UNICODE 模式发送一个字符。"""
    code = ord(char)
    inputs = (INPUT * 2)(
        _make_key_input(scan=code, flags=KEYEVENTF_UNICODE),
        _make_key_input(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
    )
    user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _activate_window(handle: int) -> bool:
    """激活窗口（仅注入按键时需要）。返回是否成功激活。"""
    try:
        user32.SetForegroundWindow(handle)
    except Exception:
        pass
    time.sleep(0.3)
    # 验证前台窗口是否是目标
    fg = user32.GetForegroundWindow()
    if fg != handle:
        # 重试一次
        try:
            user32.SetForegroundWindow(handle)
        except Exception:
            pass
        time.sleep(0.3)
        fg = user32.GetForegroundWindow()
    return fg == handle


def send_keys_to_window(handle: int, text: str) -> bool:
    """向窗口发送文本 + 回车。优先 pywinauto，失败回退剪贴板粘贴。"""
    # 激活窗口
    if not _activate_window(handle):
        logger.warning(f"无法激活窗口 {handle}，但仍尝试发送")

    # 方案1: pywinauto type_keys（对简单文本更可靠）
    try:
        from pywinauto import Application as PwaApp
        app = PwaApp(backend="uia").connect(handle=handle)
        win = app.window(handle=handle)

        # 转义 pywinauto 特殊字符
        safe = text.replace("{", "{{").replace("}", "}}")
        safe = safe.replace("+", "{+}").replace("^", "{^}")
        safe = safe.replace("%", "{%}").replace("~", "{~}")

        win.type_keys(safe, with_spaces=True, with_tabs=True, pause=0.02)
        time.sleep(0.2)
        # 回车前重新激活窗口，防止焦点丢失导致回车发不到
        _activate_window(handle)
        # pywinauto {ENTER} 在新版 Windows Terminal 中可能无效，
        # 用 SendInput VK_RETURN 双保险
        try:
            win.type_keys("{ENTER}")
        except Exception:
            pass
        time.sleep(0.1)
        _send_vk(VK_RETURN)
        logger.info(f"注入成功(pywinauto): {text[:50]}")
        return True
    except Exception as e:
        logger.warning(f"pywinauto失败: {e}, 回退剪贴板粘贴")

    # 方案2: 剪贴板粘贴 Ctrl+V（Windows Terminal 可靠接收）
    try:
        import subprocess as _sp
        # 写入剪贴板
        _sp.run(["clip.exe"], input=text.encode("utf-16le"), check=True,
                creationflags=0x08000000)  # CREATE_NO_WINDOW
        time.sleep(0.3)
        if not _activate_window(handle):
            logger.warning(f"无法激活窗口 {handle}，但仍尝试粘贴")
        # Ctrl+V
        VK_CONTROL = 0x11
        VK_V = 0x56
        inputs = (INPUT * 4)(
            _make_key_input(vk=VK_CONTROL),
            _make_key_input(vk=VK_V),
            _make_key_input(vk=VK_V, flags=KEYEVENTF_KEYUP),
            _make_key_input(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP),
        )
        user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        time.sleep(0.3)
        # 发送回车
        _send_vk(VK_RETURN)
        logger.info(f"注入成功(剪贴板): {text[:50]}")
        return True
    except Exception as e2:
        logger.exception(f"剪贴板粘贴也失败: {e2}")
        return False


# 按键别名 → 虚拟键码
VK_MAP = {
    "上": VK_UP, "up": VK_UP, "↑": VK_UP,
    "下": VK_DOWN, "down": VK_DOWN, "↓": VK_DOWN,
    "左": VK_LEFT, "left": VK_LEFT, "←": VK_LEFT,
    "右": VK_RIGHT, "right": VK_RIGHT, "→": VK_RIGHT,
    "回车": VK_RETURN, "enter": VK_RETURN,
    "tab": VK_TAB,
    "退格": VK_BACK, "backspace": VK_BACK,
    "esc": VK_ESCAPE, "取消": VK_ESCAPE,
    "空格": VK_SPACE, "space": VK_SPACE,
}


def send_raw_keys(handle: int, key_parts: list[str]) -> bool:
    """向窗口发送按键序列 — 使用 SendInput，不自动加回车。"""
    try:
        if not _activate_window(handle):
            logger.warning(f"无法激活窗口 {handle}，但仍尝试发送")
        for p in key_parts:
            p_lower = p.lower()
            if p_lower in VK_MAP:
                _send_vk(VK_MAP[p_lower])
            elif len(p) == 1:
                _send_unicode_char(p)
            else:
                # 多字符未知按键，逐字符发送
                for ch in p:
                    _send_unicode_char(ch)
            time.sleep(0.05)
        logger.info(f"按键发送: {' '.join(key_parts)}")
        return True
    except Exception as e:
        logger.exception(f"按键发送失败: {e}")
        return False


# ══════════════════════════════════════════════════════════════════
# 窗口扫描
# ══════════════════════════════════════════════════════════════════
def _get_active_projects(max_count: int = 10) -> list[str]:
    """从 ~/.claude/projects/ 扫描最近活跃的项目名（目录名解码）。"""
    import glob as _glob
    projects_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(projects_dir):
        return []
    # 找所有非 subagent 的 jsonl，按修改时间倒序
    all_jsonl = _glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))
    if not all_jsonl:
        return []
    all_jsonl.sort(key=os.path.getmtime, reverse=True)
    seen = []
    for f in all_jsonl:
        # 父目录名就是编码后的项目路径
        proj_dir = os.path.basename(os.path.dirname(f))
        if proj_dir not in seen:
            seen.append(proj_dir)
            if len(seen) >= max_count:
                break
    # 解码: "J--bedcode" → "J:\bedcode", "C--Users-Admin-Desktop-imap-1" → 取最后一段
    result = []
    for d in seen:
        # 还原路径: 第一个 -- 是盘符分隔，后续 - 是路径分隔
        parts = d.split("-")
        if len(parts) >= 2 and len(parts[0]) == 1 and parts[1] == "":
            # "J--bedcode" → ["J", "", "bedcode"] → 取最后非空段
            path_parts = [p for p in parts[2:] if p]
            label = path_parts[-1] if path_parts else d
        else:
            label = parts[-1] if parts else d
        result.append(label)
    return result


def find_claude_windows() -> list[dict]:
    """扫描所有包含 'Claude' 标题的终端窗口。"""
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
    # 排序策略: idle(✳等待输入)优先, 然后按handle降序(新窗口handle通常更大)
    order = {"idle": 0, "thinking": 1, "unknown": 2}
    results.sort(key=lambda x: (order.get(x["state"], 9), -x["handle"]))
    return results


def get_foreground_window() -> int:
    """获取当前前台窗口的handle。"""
    return user32.GetForegroundWindow()


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════
def split_text(text: str, max_len: int = 4000) -> list[str]:
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


async def send_result(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not text.strip():
        text = "(空输出)"
    safe = html.escape(text)
    chunks = split_text(safe)
    for i, chunk in enumerate(chunks):
        prefix = f"<b>[{i+1}/{len(chunks)}]</b>\n" if len(chunks) > 1 else ""
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=f"{prefix}<pre>{chunk}</pre>", parse_mode="HTML",
            )
        except Exception:
            try:
                await context.bot.send_message(chat_id=chat_id, text=f"{prefix}{chunk}")
            except Exception:
                pass


def _get_handle() -> int | None:
    handle = state["target_handle"]
    if handle:
        title = get_window_title(handle)
        if title:
            return handle
        state["target_handle"] = None
    windows = find_claude_windows()
    if windows:
        state["target_handle"] = windows[0]["handle"]
        return windows[0]["handle"]
    return None


# ══════════════════════════════════════════════════════════════════
# 监控循环 — 核心新功能
# ══════════════════════════════════════════════════════════════════
def _detect_interactive_prompt(text: str) -> str | None:
    """检测文本中是否有交互提示（选项/确认）。"""
    if not text:
        return None
    lines = text.strip().split("\n")
    tail = "\n".join(lines[-30:])
    # 常见交互模式
    prompts = [
        "Select an option",
        "Choose",
        "approve",
        "deny",
        "Yes",
        "allowedPrompts",
        "Do you want",
        "(y/n)",
        "(Y/n)",
        "❯",  # 选择器光标
        "◯",  # 单选
        "◉",  # 已选
        "☐",  # 多选框
        "☑",  # 已选框
    ]
    for p in prompts:
        if p in tail:
            return tail
    return None


def _parse_prompt_type(prompt_text: str) -> list[tuple[str, str]]:
    """解析提示类型，返回 [(按钮文字, 按键序列), ...]"""
    import re
    lower = prompt_text.lower()
    # y/n 提示
    if "(y/n)" in lower or "(y/n)?" in lower or "yes/no" in lower:
        return [("✅ Yes", "y enter"), ("❌ No", "n enter")]
    # ❯ 选择器
    if "❯" in prompt_text:
        return [("↑", "up"), ("↓", "down"), ("✓ 确认", "enter")]
    # 数字选项
    numbered = re.findall(r'(?:^|\n)\s*[\[\(]?(\d+)[\]\)]', prompt_text)
    if numbered:
        nums = sorted(set(int(n) for n in numbered if 0 < int(n) <= 9))
        if nums:
            return [(f"{n}", f"{n} enter") for n in nums]
    return []


async def _update_status(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """更新或创建状态消息 — 始终只保留一条，通过edit_text更新。"""
    msg = state.get("status_msg")
    if msg:
        try:
            await msg.edit_text(text)
            return
        except Exception:
            # edit 失败(内容相同或消息已删除)，发新消息
            pass
    try:
        state["status_msg"] = await context.bot.send_message(
            chat_id=chat_id, text=text
        )
    except Exception:
        pass


async def _delete_status() -> None:
    """删除状态消息。"""
    msg = state.get("status_msg")
    if msg:
        try:
            await msg.delete()
        except Exception:
            pass
        state["status_msg"] = None


async def _monitor_loop(
    handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """持续监控 Claude Code 状态，推送截图和通知。"""
    interval = state["screenshot_interval"]
    last_screenshot_time = 0
    was_thinking = False
    idle_count = 0
    last_state = None
    grace_period = 5  # 等待 Claude 进入 thinking 的宽限轮次 (5*3=15秒)

    try:
        # 发送初始状态
        title = await asyncio.to_thread(get_window_title, handle)
        st = detect_claude_state(title)
        if st == "thinking":
            was_thinking = True
            last_state = "thinking"
            grace_period = 0
            await _update_status(chat_id, "⏳ Claude 思考中...", context)

        while True:
            await asyncio.sleep(1.5)

            # 宽限期：等待 Claude 进入 thinking 状态
            if not was_thinking and grace_period > 0:
                grace_period -= 1
                title = await asyncio.to_thread(get_window_title, handle)
                if not title:
                    break
                st = detect_claude_state(title)
                if st == "thinking":
                    was_thinking = True
                    grace_period = 0
                    last_state = "thinking"
                    await _update_status(chat_id, "⏳ Claude 思考中...", context)
                elif grace_period == 0:
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass
                    await _delete_status()
                    break
                continue

            # 检查窗口标题
            title = await asyncio.to_thread(get_window_title, handle)
            if not title:
                break  # 窗口已关闭

            st = detect_claude_state(title)
            logger.info(f"监控状态: title={title[:30]!r} state={st} was_thinking={was_thinking} idle_count={idle_count}")

            if st == "thinking":
                was_thinking = True
                idle_count = 0
                if last_state != "thinking":
                    # 构建队列信息
                    queue_text = ""
                    if state["msg_queue"]:
                        queue_text = "\n📋 " + " → ".join(
                            f"[{i+1}]{m[:20]}" for i, m in enumerate(state["msg_queue"])
                        )
                    await _update_status(chat_id, f"⏳ Claude 思考中...{queue_text}", context)
                last_state = st

                # thinking 状态下也检测交互提示（Claude 弹选项时 spinner 可能还在转）
                text = await asyncio.to_thread(read_terminal_text, handle)
                prompt = _detect_interactive_prompt(text) if text else None
                if prompt:
                    logger.info(f"[监控] thinking 状态下检测到交互提示")
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass
                    # 生成快速回复按钮
                    qr_buttons = _parse_prompt_type(prompt)
                    markup = None
                    if qr_buttons:
                        markup = InlineKeyboardMarkup(
                            [[InlineKeyboardButton(label, callback_data=f"qr:{keys}")
                              for label, keys in qr_buttons]]
                        )
                    safe_prompt = html.escape(prompt[-1500:])
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🔘 Claude 等待你选择:\n\n{safe_prompt}",
                            reply_markup=markup,
                        )
                    except Exception:
                        pass
                    await _delete_status()
                    break

            elif st == "idle" and was_thinking:
                idle_count += 1
                last_state = st
                # 连续2次idle(3秒)确认完成，避免误判
                if idle_count >= 2:
                    # 最后再检查一次是否又变成 thinking（选择后继续执行的情况）
                    title_recheck = await asyncio.to_thread(get_window_title, handle)
                    st_recheck = detect_claude_state(title_recheck)
                    if st_recheck == "thinking":
                        logger.info(f"[监控] idle 确认后又变为 thinking，继续监控")
                        was_thinking = True
                        idle_count = 0
                        last_state = "thinking"
                        await _update_status(chat_id, "⏳ Claude 继续执行中...", context)
                        continue

                    # 先删除旧状态消息
                    await _delete_status()

                    # 发送最终截图
                    state["last_screenshot_hash"] = None
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass

                    # 从 transcript 读取完整回复（不截断）
                    term_text = await asyncio.to_thread(read_last_transcript_response)
                    if term_text and len(term_text.strip()) > 10:
                        await send_result(chat_id, term_text, context)

                    # 检查队列是否有待发消息
                    if state["msg_queue"]:
                        next_msg = state["msg_queue"].pop(0)
                        remaining = len(state["msg_queue"])
                        queue_text = ""
                        if remaining > 0:
                            queue_text = "\n📋 " + " → ".join(
                                f"[{i+1}]{m[:20]}" for i, m in enumerate(state["msg_queue"])
                            )
                        # 发新消息到最底部
                        try:
                            state["status_msg"] = await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"📤 发送队列消息:\n{next_msg[:100]}{queue_text}",
                            )
                        except Exception:
                            pass
                        # 注入消息
                        success = await asyncio.to_thread(
                            send_keys_to_window, handle, next_msg
                        )
                        if not success:
                            await _update_status(
                                chat_id,
                                "❌ 排队消息发送失败，窗口可能已关闭",
                                context,
                            )
                            break
                        # 重置状态，继续监控等待下一次完成
                        was_thinking = False
                        idle_count = 0
                        last_state = None
                        grace_period = 5
                        # 不 break，继续循环
                    else:
                        # 发截图+按钮让用户判断是完成还是等待选择
                        buttons = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("✅ 已完成", callback_data="monitor:done"),
                                InlineKeyboardButton("🔘 需要选择", callback_data="monitor:waiting"),
                            ],
                        ])
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="Claude 已停止思考，请查看截图：",
                                reply_markup=buttons,
                            )
                        except Exception:
                            pass
                        break
            else:
                idle_count = 0

            # 定期截图（不打断思考）
            now = time.time()
            if now - last_screenshot_time >= interval:
                last_screenshot_time = now
                img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                if img_data:
                    img_hash = _image_hash(img_data)
                    if img_hash != state["last_screenshot_hash"]:
                        state["last_screenshot_hash"] = img_hash
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass

    except asyncio.CancelledError:
        await _delete_status()
    except Exception as e:
        logger.error(f"监控循环异常: {e}")


def _cancel_monitor():
    """取消正在运行的监控循环。"""
    task = state.get("monitor_task")
    if task and not task.done():
        task.cancel()
    state["monitor_task"] = None


def _start_monitor(handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """启动监控循环（取消旧的）。"""
    _cancel_monitor()
    state["monitor_task"] = asyncio.create_task(
        _monitor_loop(handle, chat_id, context)
    )


# ══════════════════════════════════════════════════════════════════
# 流式模式 — 每条消息启动 claude -p 子进程，实时转发输出
# ══════════════════════════════════════════════════════════════════
def _find_git_bash() -> str:
    """自动检测 Git Bash 路径。"""
    # 1. 环境变量优先
    env_path = os.environ.get("GIT_BASH_PATH", "")
    if env_path and os.path.isfile(env_path):
        return env_path
    # 2. 常见安装位置
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # 3. where 命令查找
    try:
        result = subprocess.run(
            ["where", "bash"], capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            if "git" in line.lower() and os.path.isfile(line.strip()):
                return line.strip()
    except Exception:
        pass
    # 4. 回退默认
    logger.warning("未找到 Git Bash，使用默认路径")
    return r"C:\Program Files\Git\bin\bash.exe"


GIT_BASH_PATH = _find_git_bash()
logger.info(f"Git Bash: {GIT_BASH_PATH}")


def _kill_stream_proc():
    """终止流式子进程。"""
    proc = state.get("stream_proc")
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    state["stream_proc"] = None
    task = state.get("stream_task")
    if task and not task.done():
        task.cancel()
    state["stream_task"] = None


async def _stream_reader(proc, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """逐行读取子进程 stdout，解析 JSON 并实时转发到 Telegram。"""
    loop = asyncio.get_event_loop()
    buf = ""
    last_flush = time.time()
    notified_thinking = False
    line_count = 0

    logger.info(f"[流式] reader 启动, PID={proc.pid}")

    try:
        while True:
            try:
                line_bytes = await loop.run_in_executor(None, proc.stdout.readline)
            except Exception as e:
                logger.error(f"[流式] stdout 读取异常: {e}")
                break
            if not line_bytes:
                logger.info(f"[流式] stdout EOF, 共读取 {line_count} 行")
                # 检查 stderr
                try:
                    stderr_out = proc.stderr.read()
                    if stderr_out:
                        stderr_text = stderr_out.decode("utf-8", errors="replace").strip()
                        logger.error(f"[流式] stderr: {stderr_text[:500]}")
                except Exception:
                    pass
                break
            line_count += 1
            try:
                line = line_bytes.decode("utf-8", errors="replace").strip()
            except Exception as e:
                logger.warning(f"[流式] 解码失败: {e}")
                continue
            if not line:
                continue

            logger.debug(f"[流式] 原始行 #{line_count}: {line[:200]}")

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"[流式] 非JSON行 #{line_count}: {line[:100]}")
                continue

            msg_type = data.get("type", "")
            logger.info(f"[流式] 消息类型: {msg_type}")

            if msg_type == "assistant":
                content_raw = data.get("message", {}).get("content", [])
                content_list = content_raw if isinstance(content_raw, list) else []
                for item in content_list:
                    item_type = item.get("type", "")
                    if item_type == "text":
                        text = item.get("text", "")
                        if text:
                            buf += text
                            logger.info(f"[流式] 收到文本 ({len(text)}字): {text[:80]}")
                    elif item_type == "thinking":
                        logger.info(f"[流式] 收到 thinking 块")
                        if not notified_thinking:
                            notified_thinking = True
                            await _update_status(chat_id, "⏳ Claude 思考中...", context)
                    elif item_type == "tool_use":
                        tool_name = item.get("name", "unknown")
                        logger.info(f"[流式] 工具调用: {tool_name}")
                        # 更新状态提示工具调用
                        await _update_status(chat_id, f"🔧 调用工具: {tool_name}", context)
                    else:
                        logger.info(f"[流式] 其他内容类型: {item_type}")

                # 不再增量发送，只更新状态提示让用户知道在工作
                now = time.time()
                if buf and now - last_flush > 5:
                    await _update_status(chat_id, f"⏳ Claude 回复中... ({len(buf)}字)", context)
                    last_flush = now

            elif msg_type == "result":
                logger.info(f"[流式] 收到 result, buf总计={len(buf)}字")
                await _delete_status()
                cost = data.get("total_cost_usd", 0)
                # 一次性发送完整回复，保证格式完整
                if buf:
                    chunks = split_text(buf, 4000)
                    for chunk in chunks:
                        safe = html.escape(chunk)
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id, text=f"<pre>{safe}</pre>", parse_mode="HTML",
                            )
                        except Exception:
                            await context.bot.send_message(chat_id=chat_id, text=chunk)
                    buf = ""
                cost_text = f" | ${cost:.4f}" if cost else ""
                await context.bot.send_message(
                    chat_id=chat_id, text=f"✅ 完成{cost_text}",
                )
            else:
                logger.info(f"[流式] 未处理类型: {msg_type}, keys={list(data.keys())}")

    except asyncio.CancelledError:
        logger.info("[流式] reader 被取消")
    except Exception as e:
        logger.error(f"[流式] reader 异常: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 流式读取异常: {e}")

    ret = proc.poll()
    logger.info(f"[流式] 子进程退出码: {ret}")


async def _stream_send(text: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """启动 claude -p 子进程处理消息，实时转发输出。"""
    # 终止上一个还在运行的流式进程
    _kill_stream_proc()

    logger.info(f"[流式] 启动子进程, prompt={text[:80]}, cwd={state['cwd']}")
    await _update_status(chat_id, "⏳ 启动 Claude...", context)

    env = os.environ.copy()
    env["CLAUDE_CODE_GIT_BASH_PATH"] = GIT_BASH_PATH

    cmd = [
        "claude.cmd", "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--add-dir", state["cwd"],
        text,
    ]
    logger.info(f"[流式] 命令: {' '.join(cmd[:7])} ...")

    try:
        proc = await asyncio.to_thread(
            lambda: subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=state["cwd"],
                env=env,
            )
        )
        logger.info(f"[流式] 子进程已启动, PID={proc.pid}")
        state["stream_proc"] = proc
        state["stream_task"] = asyncio.create_task(
            _stream_reader(proc, chat_id, context)
        )
    except Exception as e:
        logger.error(f"[流式] 启动失败: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 流式启动失败: {e}")


# ══════════════════════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════════════════════
async def auth_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and update.effective_user.id not in ALLOWED_USERS:
        raise ApplicationHandlerStop()


# ══════════════════════════════════════════════════════════════════
# 命令处理
# ══════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    windows = await asyncio.to_thread(find_claude_windows)
    win_info = ""
    if windows:
        if not state["target_handle"]:
            state["target_handle"] = windows[0]["handle"]
        for w in windows:
            marker = " &lt;&lt; 当前" if w["handle"] == state["target_handle"] else ""
            st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(w["state"], "?")
            label_tag = f" 📌{w['label']}" if w.get("label") else ""
            win_info += (
                f"\n  • [{st_label}]{label_tag}{marker}"
                f"\n    handle: <code>{w['handle']}</code>"
            )
    else:
        win_info = "\n  未找到 Claude Code 窗口!"

    monitor_status = "运行中" if state.get("monitor_task") and not state["monitor_task"].done() else "未启动"
    text = (
        "<b>BedCode v5 在线</b>\n\n"
        "<b>使用方式：</b>\n"
        "• 直接发消息 → 注入 Claude Code 终端\n"
        "• <code>!命令</code> → 执行 Shell 命令\n"
        "• /key 按键 → 发按键(选选项用)\n"
        "• /delay 秒数 → 截图间隔\n"
        "• /auto → 开关自动监控\n"
        "• /cd 路径 → 切换目录\n\n"
        f"<b>自动监控：</b> {'开启' if state['auto_monitor'] else '关闭'}"
        f" ({state['screenshot_interval']}s)\n"
        f"<b>监控循环：</b> {monitor_status}\n"
        f"<b>窗口：</b>{win_info}"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=REPLY_KEYBOARD)


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handle = _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，先 /windows")
        return
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if img_data:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_data)
    else:
        await update.message.reply_text("截屏失败")


async def cmd_grab(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """抓取终端文本 — 通过 UIA 读取（idle 状态安全，thinking 时可能打断）。"""
    handle = _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，先 /windows")
        return

    # 检测状态，thinking 时警告
    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)
    if st == "thinking":
        await update.message.reply_text("⚠️ Claude 正在思考，抓取文本可能打断！改用 /screenshot 截图")
        return

    term_text = await asyncio.to_thread(read_terminal_text, handle)
    if term_text and len(term_text.strip()) > 10:
        await send_result(update.effective_chat.id, term_text, context)
    else:
        # 文本抓取失败，回退截图
        await update.message.reply_text("文本抓取为空，发送截图代替")
        img_data = await asyncio.to_thread(capture_window_screenshot, handle)
        if img_data:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_data)


async def cmd_delay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        await update.message.reply_text(f"当前: {state['screenshot_interval']}s\n用法: /delay 秒数")
        return
    try:
        delay = max(3, min(300, int(args)))
        state["screenshot_interval"] = delay
        await update.message.reply_text(f"截图间隔设为 {delay}s")
    except ValueError:
        await update.message.reply_text("请输入数字")


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state["auto_monitor"] = not state["auto_monitor"]
    await update.message.reply_text(f"自动监控: {'开启' if state['auto_monitor'] else '关闭'}")


async def cmd_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/key <按键> — 发送特殊按键到终端。"""
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        await update.message.reply_text(
            "<b>用法：</b> <code>/key 按键</code>\n\n"
            "<b>支持的按键：</b>\n"
            "• 数字: <code>/key 1</code> <code>/key 2</code> <code>/key 3</code>\n"
            "• 方向: <code>/key 上</code> <code>/key 下</code>\n"
            "• 确认: <code>/key enter</code> <code>/key y</code>\n"
            "• 取消: <code>/key esc</code> <code>/key n</code>\n"
            "• 其他: <code>/key tab</code> <code>/key space</code>\n\n"
            "<b>组合：</b> <code>/key 下 下 enter</code>（选第3项）",
            parse_mode="HTML",
        )
        return

    handle = _get_handle()
    if not handle:
        await update.message.reply_text("未锁定窗口，先 /windows")
        return

    parts = args.split()
    success = await asyncio.to_thread(send_raw_keys, handle, parts)
    if success:
        await update.message.reply_text(f"已发送: {args}")
        # 3秒后截屏看结果
        asyncio.create_task(_quick_screenshot(handle, update.effective_chat.id, context))
    else:
        await update.message.reply_text("按键发送失败")


async def _quick_screenshot(handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await asyncio.sleep(3)
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if img_data:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
        except Exception:
            pass


async def cmd_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handle = _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，先 /windows")
        return
    _start_monitor(handle, update.effective_chat.id, context)
    await update.message.reply_text("监控已启动")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _cancel_monitor()
    await update.message.reply_text("监控已停止")


async def cmd_windows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    windows = await asyncio.to_thread(find_claude_windows)
    if not windows:
        await update.message.reply_text("未找到 Claude Code 窗口\n用 /new 启动新实例")
        return
    # 获取活跃项目列表作为参考
    projects = await asyncio.to_thread(_get_active_projects, len(windows))
    proj_hint = ""
    if projects:
        proj_hint = "\n\n📂 最近活跃项目: " + ", ".join(projects)

    lines = ["<b>Claude Code 窗口：</b>"]
    buttons = []
    for i, w in enumerate(windows):
        current = w["handle"] == state["target_handle"]
        marker = " ✔" if current else ""
        st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(w["state"], "?")
        label = w.get("label", "")
        label_tag = f" 📌{label}" if label else f" #{i+1}"
        lines.append(
            f"• [{st_label}]{label_tag}{marker}"
        )
        btn_label = f"📌{label}" if label else f"#{i+1}"
        btn_text = f"{'✔ ' if current else ''}{st_label} | {btn_label}"
        buttons.append([
            InlineKeyboardButton(btn_text, callback_data=f"target:{w['handle']}"),
            InlineKeyboardButton("✏️", callback_data=f"label:{w['handle']}"),
        ])
    buttons.append([InlineKeyboardButton("🆕 启动新实例", callback_data="new_claude")])
    await update.message.reply_text(
        "\n".join(lines) + proj_hint,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    # 自动发每个窗口的截图缩略图帮助区分
    for i, w in enumerate(windows):
        img_data = await asyncio.to_thread(capture_window_screenshot, w["handle"])
        if img_data:
            label = w.get("label", "") or f"#{i+1}"
            st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(w["state"], "?")
            await update.message.reply_photo(
                photo=img_data,
                caption=f"{label} [{st_label}]",
            )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 inline 按钮点击。"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("target:"):
        handle = int(data.split(":")[1])
        title = await asyncio.to_thread(get_window_title, handle)
        if not title:
            await query.edit_message_text("窗口已关闭，请重新 /windows")
            return
        state["target_handle"] = handle
        st = detect_claude_state(title)
        st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(st, "?")
        label = state["window_labels"].get(handle, "")
        label_tag = f" 📌{label}" if label else ""
        await query.edit_message_text(
            f"✅ 已切换到: [{st_label}]{label_tag}\nHandle: <code>{handle}</code>",
            parse_mode="HTML",
        )
        # 发截图确认
        img_data = await asyncio.to_thread(capture_window_screenshot, handle)
        if img_data:
            await context.bot.send_photo(
                chat_id=query.message.chat_id, photo=img_data,
                caption=f"当前窗口{label_tag}",
            )

    elif data.startswith("label:"):
        handle = int(data.split(":")[1])
        # 存储 handle 到 context，等待用户下一条消息作为标签
        context.user_data["pending_label_handle"] = handle
        await query.edit_message_text(
            f"✏️ 请发送窗口 <code>{handle}</code> 的标签名（如项目名）：",
            parse_mode="HTML",
        )

    elif data.startswith("qr:"):
        keys = data[3:]
        handle = _get_handle()
        if not handle:
            await query.edit_message_text("❌ 窗口已关闭")
            return
        key_parts = keys.split()
        success = await asyncio.to_thread(send_raw_keys, handle, key_parts)
        if success:
            await query.edit_message_text(f"✅ 已发送: {keys}")
            if state["auto_monitor"]:
                _start_monitor(handle, query.message.chat_id, context)
        else:
            await query.edit_message_text("❌ 发送失败")

    elif data == "queue:view":
        if not state["msg_queue"]:
            await query.edit_message_text("📋 队列为空")
            return
        queue_list = "\n".join(
            f"{i+1}. {msg[:80]}{'...' if len(msg) > 80 else ''}"
            for i, msg in enumerate(state["msg_queue"])
        )
        await query.edit_message_text(
            f"📋 当前队列 ({len(state['msg_queue'])} 条):\n\n{queue_list}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑 清空", callback_data="queue:clear"),
            ]]),
        )

    elif data == "queue:clear":
        count = len(state["msg_queue"])
        state["msg_queue"].clear()
        await query.edit_message_text(f"🗑 已清空队列 ({count} 条消息)")

    elif data == "new_claude":
        # 弹出路径选择菜单
        buttons = _build_dir_buttons()
        await query.edit_message_text(
            "📁 选择新实例的工作目录：",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("newdir:"):
        chosen = data[7:]
        if chosen == "manual":
            state["_waiting_new_dir"] = True
            await query.edit_message_text("✏️ 请直接发送目标路径，例如：\n<code>D:\\projects\\myapp</code>", parse_mode="HTML")
            return
        if chosen == "cwd":
            chosen = state["cwd"]
        if not os.path.isdir(chosen):
            await query.edit_message_text(f"❌ 目录不存在: {chosen}")
            return
        # 保存选择的目录，弹出窗口模式选择
        state["_new_dir"] = chosen
        buttons = [
            [InlineKeyboardButton("🪟 新窗口", callback_data="newmode:window")],
            [InlineKeyboardButton("📑 新标签页", callback_data="newmode:tab")],
        ]
        await query.edit_message_text(
            f"📂 {chosen}\n选择启动方式：",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("newmode:"):
        mode = data[8:]
        chosen = state.get("_new_dir", state["cwd"])
        new_window = mode == "window"
        mode_text = "新窗口" if new_window else "新标签页"
        await query.edit_message_text(f"🚀 正在以{mode_text}启动...\n📂 {chosen}")
        await _launch_new_claude(query.message.chat_id, context, chosen, new_window=new_window)

    elif data == "monitor:done":
        await query.edit_message_text("✅ Claude 完成，等待输入")

    elif data == "monitor:waiting":
        await query.edit_message_text("🔘 Claude 等待选择，请用 /key 发送按键")
        # 重新截一张图方便用户看清选项
        handle = _get_handle()
        if handle:
            img_data = await asyncio.to_thread(capture_window_screenshot, handle)
            if img_data:
                try:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_data)
                except Exception:
                    pass


async def _launch_new_claude(chat_id: int, context: ContextTypes.DEFAULT_TYPE, work_dir: str = None, new_window: bool = False) -> None:
    """启动新的 Claude Code 实例。"""
    if work_dir is None:
        work_dir = state["cwd"]
    _save_recent_dir(work_dir)
    try:
        wt_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
        git_bash = os.environ.get("GIT_BASH_PATH", GIT_BASH_PATH)
        # 写临时 bat：设环境变量 + 启动 claude
        import tempfile
        bat_path = os.path.join(tempfile.gettempdir(), "bedcode_launch.bat")
        with open(bat_path, "w", encoding="ascii") as f:
            f.write(f"@set CLAUDE_CODE_GIT_BASH_PATH={git_bash}\n")
            f.write(f"@cd /d \"{work_dir}\"\n")
            f.write("@claude\n")
        if new_window:
            cmd = [wt_path, "-w", "new", bat_path]
        else:
            cmd = [wt_path, "-w", "0", "nt", bat_path]
        await asyncio.to_thread(lambda: subprocess.Popen(cmd))
        mode_text = "新窗口" if new_window else "新标签页"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚀 已在{mode_text}启动 Claude Code\n📂 {work_dir}\n⏳ 等待启动并自动选择...",
        )
        # 等 Claude Code 加载完成后自动按 1 + 回车选第一个选项
        await asyncio.sleep(8)
        def _auto_select():
            _send_unicode_char("1")
            time.sleep(0.1)
            _send_vk(VK_RETURN)
        await asyncio.to_thread(_auto_select)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ 已自动选择第一个选项\n发 /windows 扫描并锁定新实例",
        )
    except Exception as e:
        logger.exception(f"启动 Claude Code 失败: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ 启动失败: {e}",
        )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/new — 启动新 Claude Code 实例（先选路径）。"""
    args = " ".join(context.args).strip() if context.args else ""
    if args and os.path.isdir(args):
        # /new <路径> 直接启动
        await update.message.reply_text(f"🚀 正在启动新实例...\n📂 {args}")
        await _launch_new_claude(update.effective_chat.id, context, args)
        return
    # 弹出路径选择菜单
    buttons = _build_dir_buttons()
    await update.message.reply_text(
        "📁 选择新实例的工作目录：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_switch_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """切换窗口模式 / 流式模式。"""
    if state["stream_mode"]:
        state["stream_mode"] = False
        _kill_stream_proc()
        await update.message.reply_text(
            "🪟 已切换到 <b>窗口模式</b>\n消息将注入到 Claude Code 窗口",
            parse_mode="HTML", reply_markup=REPLY_KEYBOARD,
        )
    else:
        state["stream_mode"] = True
        await update.message.reply_text(
            "📡 已切换到 <b>流式模式</b>\n消息将通过子进程实时通信\n下一条消息将启动流式会话",
            parse_mode="HTML", reply_markup=REPLY_KEYBOARD,
        )


async def cmd_cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        await update.message.reply_text(f"当前: <code>{html.escape(state['cwd'])}</code>", parse_mode="HTML")
        return
    target = os.path.abspath(os.path.join(state["cwd"], args))
    if os.path.isdir(target):
        state["cwd"] = target
        await update.message.reply_text(f"已切换: <code>{html.escape(target)}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text(f"不存在: <code>{html.escape(target)}</code>", parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════
# 消息处理
# ══════════════════════════════════════════════════════════════════
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
os.makedirs(IMG_DIR, exist_ok=True)
MSG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages")
os.makedirs(MSG_DIR, exist_ok=True)

# pywinauto 无法处理的特殊字符
_UNSAFE_CHARS = set('{}"$\\')


def _needs_file(text: str) -> bool:
    """判断消息是否需要保存为文件（过长或含特殊字符）。"""
    if len(text) > 200:
        return True
    return bool(_UNSAFE_CHARS & set(text))


def _save_msg_file(text: str) -> str:
    """将消息保存为文件，返回文件路径。"""
    ts = int(time.time())
    filepath = os.path.join(MSG_DIR, f"msg_{ts}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return filepath


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理手机发来的图片 — 下载保存后注入路径到 Claude Code。"""
    photo = update.message.photo[-1]  # 取最大分辨率
    caption = (update.message.caption or "").strip()

    # 下载图片
    file = await context.bot.get_file(photo.file_id)
    ts = int(time.time())
    filename = f"tg_{ts}_{photo.file_unique_id}.jpg"
    filepath = os.path.join(IMG_DIR, filename)
    await file.download_to_drive(filepath)
    logger.info(f"图片已保存: {filepath}")

    # 构建注入文本：图片路径 + 用户附言
    if caption:
        inject_text = f"{caption} {filepath}"
    else:
        inject_text = f"请分析这个图片 {filepath}"

    await _inject_to_claude(update, context, inject_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    # 处理标签设置（来自 /windows 的 ✏️ 按钮）
    pending_handle = context.user_data.get("pending_label_handle")
    if pending_handle is not None:
        del context.user_data["pending_label_handle"]
        state["window_labels"][pending_handle] = text[:20]
        _save_labels()
        await update.message.reply_text(
            f"✅ 窗口 <code>{pending_handle}</code> 已标记为 📌<b>{html.escape(text[:20])}</b>",
            parse_mode="HTML",
        )
        return

    # 常驻按钮路由
    BUTTON_MAP = {
        "📷 截屏": cmd_screenshot,
        "🪟 窗口": cmd_windows,
        "🆕 新实例": cmd_new,
        "👀 监控": cmd_watch,
        "⏹ 停止": cmd_stop,
        "🔄 状态": cmd_start,
        "🔀 切换模式": cmd_switch_mode,
    }
    if text in BUTTON_MAP:
        await BUTTON_MAP[text](update, context)
        return

    # 手动输入路径 → 启动新实例
    if state.get("_waiting_new_dir"):
        state["_waiting_new_dir"] = False
        if os.path.isdir(text):
            await update.message.reply_text(f"🚀 正在启动新实例...\n📂 {text}")
            await _launch_new_claude(update.effective_chat.id, context, text)
        else:
            await update.message.reply_text(f"❌ 目录不存在: <code>{html.escape(text)}</code>\n请重新 /new", parse_mode="HTML")
        return

    if text.startswith("!"):
        cmd = text[1:].strip()
        if cmd:
            await _run_shell(update, context, cmd)
        return

    # 流式模式 → 走子进程通道
    if state["stream_mode"]:
        await _stream_send(text, update.effective_chat.id, context)
        return

    await _inject_to_claude(update, context, text)


async def _inject_to_claude(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    handle = _get_handle()
    if not handle:
        await update.message.reply_text("未找到 Claude Code 窗口!\n请先启动 Claude Code，然后 /windows")
        return

    # 长消息或含特殊字符 → 保存为文件，注入路径
    inject_text = text
    if _needs_file(text):
        filepath = _save_msg_file(text)
        inject_text = f"请阅读这个文件并按其中的指示操作 {filepath}"
        logger.info(f"长消息保存为文件: {filepath}")

    # 检测 Claude 当前状态
    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)

    if st == "thinking":
        # Claude 正在思考，消息入队列（存原始 inject_text）
        if len(state["msg_queue"]) >= 50:
            await update.message.reply_text("⚠️ 队列已满 (50条)，请等待 Claude 完成")
            return
        state["msg_queue"].append(inject_text)
        state["queue_chat_id"] = update.effective_chat.id
        # 用状态消息显示队列情况（edit已有消息）
        queue_text = "📋 " + " → ".join(
            f"[{i+1}]{m[:20]}" for i, m in enumerate(state["msg_queue"])
        )
        queue_buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 查看队列", callback_data="queue:view"),
            InlineKeyboardButton("🗑 清空队列", callback_data="queue:clear"),
        ]])
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⏳ Claude 思考中...\n{queue_text}",
                reply_markup=queue_buttons,
            )
        except Exception:
            pass
        # 确保监控循环在运行（它会在 idle 后自动发送队列）
        if not state.get("monitor_task") or state["monitor_task"].done():
            _start_monitor(handle, update.effective_chat.id, context)
        return

    # Claude 空闲，直接注入
    logger.info(f"注入到窗口 {handle}: {inject_text[:80]}")
    success = await asyncio.to_thread(send_keys_to_window, handle, inject_text)

    if not success:
        state["target_handle"] = None
        await _update_status(update.effective_chat.id, "❌ 发送失败，窗口可能已关闭\n发 /windows 重新扫描", context)
        return

    await _update_status(update.effective_chat.id, "✅ 已发送", context)

    # 启动监控循环
    if state["auto_monitor"]:
        _start_monitor(handle, update.effective_chat.id, context)


async def _run_shell(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd: str) -> None:
    thinking = await update.message.reply_text(
        f"执行: <code>{html.escape(cmd[:80])}</code>", parse_mode="HTML"
    )
    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(
                [GIT_BASH_PATH, "-c", cmd], capture_output=True, text=True,
                timeout=SHELL_TIMEOUT, cwd=state["cwd"],
            )
        )
        output = result.stdout or ""
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if not output.strip():
            output = f"(完成，退出码: {result.returncode})"
        try:
            await thinking.delete()
        except Exception:
            pass
        await send_result(update.effective_chat.id, output, context)
    except subprocess.TimeoutExpired:
        await thinking.edit_text(f"超时 ({SHELL_TIMEOUT}s)")
    except Exception as e:
        await thinking.edit_text(f"出错: {html.escape(str(e))}", parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════
# 错误处理
# ══════════════════════════════════════════════════════════════════
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"异常: {context.error}")


# ══════════════════════════════════════════════════════════════════
# 启动
# ══════════════════════════════════════════════════════════════════
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("命令菜单已注册")


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("错误: 请在 .env 中设置 TELEGRAM_BOT_TOKEN")
        return
    if not ALLOWED_USERS:
        print("错误: 请在 .env 中设置 ALLOWED_USER_IDS")
        return

    windows = find_claude_windows()
    if windows:
        state["target_handle"] = windows[0]["handle"]
        logger.info(f"锁定窗口: {windows[0]['title']} ({windows[0]['handle']})")
    else:
        logger.warning("未找到 Claude Code 窗口")

    logger.info(f"BedCode v5 启动 | 用户: {ALLOWED_USERS}")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_error_handler(error_handler)
    app.add_handler(TypeHandler(Update, auth_gate), group=-1)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    app.add_handler(CommandHandler("grab", cmd_grab))
    app.add_handler(CommandHandler("key", cmd_key))
    app.add_handler(CommandHandler("watch", cmd_watch))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("delay", cmd_delay))
    app.add_handler(CommandHandler("auto", cmd_auto))
    app.add_handler(CommandHandler("windows", cmd_windows))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("cd", cmd_cd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
