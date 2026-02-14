#!/usr/bin/env python3
"""BedCode v5 — Telegram Bot 远程操控 Claude Code"""
import signal

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from config import BOT_TOKEN, ALLOWED_USERS, BOT_COMMANDS, state, logger
from claude_detect import find_claude_windows
from utils import _load_labels
from stream_mode import _kill_stream_proc
from handlers import (
    auth_gate,
    cmd_start, cmd_screenshot, cmd_grab, cmd_key,
    cmd_watch, cmd_stop, cmd_delay, cmd_auto,
    cmd_windows, cmd_new, cmd_cd, cmd_history, cmd_reload,
    callback_handler, handle_message, handle_photo,
    handle_voice, handle_document,
)
from monitor import _start_passive_monitor

# 加载持久化标签
state["window_labels"] = _load_labels()


async def error_handler(update: object, context) -> None:
    logger.error(f"异常: {context.error}")


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("命令菜单已注册")
    # 启动常驻被动监控（等第一条消息获取 chat_id 后自动生效）
    _start_passive_monitor(application)


def _cleanup():
    _kill_stream_proc()
    for key in ("monitor_task", "passive_monitor_task"):
        task = state.get(key)
        if task and not task.done():
            task.cancel()
    logger.info("BedCode 清理完成")


def main() -> None:
    signal.signal(signal.SIGINT, lambda *_: _cleanup())
    signal.signal(signal.SIGTERM, lambda *_: _cleanup())
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
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
