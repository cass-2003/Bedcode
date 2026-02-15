#!/usr/bin/env python3
"""BedCode v6 — Telegram Bot + Web API 远程操控 Claude Code"""
import os
import asyncio
import signal
import subprocess

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
from utils import _load_labels, _load_templates, _load_panel, _load_aliases, _load_state, _save_state
from stream_mode import _kill_stream_proc
from handlers import (
    auth_gate,
    cmd_start, cmd_screenshot, cmd_grab, cmd_key,
    cmd_watch, cmd_stop, cmd_break, cmd_delay, cmd_auto,
    cmd_windows, cmd_new, cmd_cd, cmd_history, cmd_reload,
    cmd_cost, cmd_export, cmd_undo,
    cmd_diff, cmd_log, cmd_search, cmd_schedule,
    cmd_tpl, cmd_proj,
    cmd_panel, cmd_clip, cmd_autoyes,
    cmd_quiet, cmd_alias, cmd_batch, cmd_tts, cmd_ocr,
    callback_handler, handle_message, handle_photo,
    handle_voice, handle_document,
)
from monitor import _start_passive_monitor

# 加载持久化状态
state["window_labels"] = _load_labels()
state["templates"] = _load_templates()
_panel_rows = _load_panel()
if _panel_rows:
    from handlers import _build_panel_markup
    state["custom_panel"] = _build_panel_markup(_panel_rows)
state["aliases"] = _load_aliases()
_load_state()


async def error_handler(update: object, context) -> None:
    logger.error(f"异常: {context.error}")


def _cleanup():
    _save_state()
    _kill_stream_proc()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    for key in ("monitor_task", "passive_monitor_task"):
        task = state.get(key)
        if task and not task.done():
            if loop and loop.is_running():
                loop.call_soon_threadsafe(task.cancel)
            else:
                task.cancel()
    logger.info("BedCode 清理完成")


def _build_tg_app() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_error_handler(error_handler)
    app.add_handler(TypeHandler(Update, auth_gate), group=-1)

    for name, handler in [
        ("start", cmd_start), ("screenshot", cmd_screenshot), ("grab", cmd_grab),
        ("key", cmd_key), ("watch", cmd_watch), ("stop", cmd_stop),
        ("break", cmd_break), ("delay", cmd_delay), ("auto", cmd_auto),
        ("windows", cmd_windows), ("new", cmd_new), ("cd", cmd_cd),
        ("history", cmd_history), ("cost", cmd_cost), ("export", cmd_export),
        ("undo", cmd_undo), ("reload", cmd_reload), ("diff", cmd_diff),
        ("log", cmd_log), ("search", cmd_search), ("schedule", cmd_schedule),
        ("proj", cmd_proj), ("tpl", cmd_tpl), ("panel", cmd_panel),
        ("clip", cmd_clip), ("autoyes", cmd_autoyes), ("quiet", cmd_quiet),
        ("alias", cmd_alias), ("batch", cmd_batch), ("tts", cmd_tts), ("ocr", cmd_ocr),
    ]:
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    return app


async def run_all():
    # 1. 扫描窗口
    windows = find_claude_windows()
    if windows:
        state["target_handle"] = windows[0]["handle"]
        logger.info(f"锁定窗口: {windows[0]['title']} ({windows[0]['handle']})")
    else:
        logger.warning("未找到 Claude Code 窗口")

    # 2. 启动 TG bot（非阻塞）
    tg_app = _build_tg_app()
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    await tg_app.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Telegram bot 已启动")

    # 3. 启动被动监控
    _start_passive_monitor(tg_app)

    # 4. 启动 FastAPI + uvicorn
    from api.app import app as fastapi_app, setup_routes, API_TOKEN
    setup_routes()

    api_port = int(os.environ.get("API_PORT", "8080"))
    logger.info(f"BedCode v6 启动 | TG用户: {ALLOWED_USERS} | API: http://0.0.0.0:{api_port} | Token: {API_TOKEN}")

    # 5. 启动 Cloudflare Tunnel
    cf_proc = None
    cf_exe = os.path.expanduser("~/cloudflared.exe")
    cf_config = os.path.expanduser("~/.cloudflared/bedcode.yml")
    if os.path.isfile(cf_exe) and os.path.isfile(cf_config):
        cf_proc = subprocess.Popen(
            [cf_exe, "tunnel", "--config", cf_config, "run", "bedcode"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        logger.info("Cloudflare Tunnel 已启动 → https://bed.haiio.xyz")
    else:
        logger.warning("cloudflared 未找到，跳过隧道启动")

    import uvicorn
    uvi_config = uvicorn.Config(
        fastapi_app, host="0.0.0.0", port=api_port,
        log_level="warning", access_log=False,
    )
    server = uvicorn.Server(uvi_config)

    try:
        await server.serve()
    finally:
        if cf_proc:
            cf_proc.terminate()
            cf_proc.wait(timeout=5)
            logger.info("Cloudflare Tunnel 已停止")
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        _cleanup()


def main() -> None:
    signal.signal(signal.SIGINT, lambda *_: _cleanup())
    signal.signal(signal.SIGTERM, lambda *_: _cleanup())
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("错误: 请在 .env 中设置 TELEGRAM_BOT_TOKEN")
        return
    if not ALLOWED_USERS:
        print("错误: 请在 .env 中设置 ALLOWED_USER_IDS")
        return

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
