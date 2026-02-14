"""BedCode 配置、日志、全局状态。"""
import os
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    ReplyKeyboardMarkup, KeyboardButton,
)

# ── 加载配置 ─────────────────────────────────────────────────────
load_dotenv()

# 绕过代理直连 Telegram API
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = set()
for _uid in os.environ.get("ALLOWED_USER_IDS", "").split(","):
    _uid = _uid.strip()
    if _uid:
        try:
            ALLOWED_USERS.add(int(_uid))
        except ValueError:
            print(f"警告: 无效的用户ID '{_uid}'，已跳过")
SHELL_TIMEOUT = int(os.environ.get("SHELL_TIMEOUT", "120"))
WORK_DIR = os.environ.get("WORK_DIR", str(Path.home()))
SCREENSHOT_DELAY = int(os.environ.get("SCREENSHOT_DELAY", "15"))

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LABELS_FILE = os.path.join(_BASE_DIR, "window_labels.json")
RECENT_DIRS_FILE = os.path.join(_BASE_DIR, "recent_dirs.json")

# ── 日志 ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(os.path.join(_BASE_DIR, "bot.log"), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"),
    ],
)
logger = logging.getLogger("bedcode")

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
    BotCommand("history", "查看最近20条消息历史"),
    BotCommand("reload", "热重载配置"),
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
    "monitor_task": None,
    "msg_queue": deque(maxlen=50),
    "queue_chat_id": None,
    "status_msg": None,
    "stream_proc": None,
    "stream_task": None,
    "stream_mode": False,
    "window_labels": {},
    "last_screenshot_hash": None,
    "cmd_history": deque(maxlen=20),
    "chat_id": None,
    "passive_monitor_task": None,
}
