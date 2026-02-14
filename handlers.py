"""Telegram 命令/回调/消息处理。"""
import os
import html
import time
import asyncio
import subprocess
import tempfile
import pathlib
import logging

from telegram import (
    Update,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    ApplicationHandlerStop,
    ContextTypes,
)

import config
from config import (
    state, ALLOWED_USERS, READONLY_USERS, SHELL_TIMEOUT, REPLY_KEYBOARD,
)
from win32_api import (
    capture_window_screenshot, get_window_title,
    send_keys_to_window, send_raw_keys,
    _send_unicode_char, _send_vk, VK_RETURN,
    copy_image_to_clipboard, paste_image_to_window,
    send_ctrl_c, send_ctrl_z,
    get_clipboard_text, set_clipboard_text,
)
from claude_detect import (
    detect_claude_state, find_claude_windows,
    read_terminal_text, _get_active_projects, _get_active_projects_detail,
)
from monitor import _update_status, _delete_status, _start_monitor, _cancel_monitor, _queue_lock
from stream_mode import _stream_send, _kill_stream_proc, GIT_BASH_PATH
from utils import (
    send_result, _get_handle, _save_labels, _build_dir_buttons,
    _save_recent_dir, _needs_file, _save_msg_file, IMG_DIR,
    _save_templates, _load_panel, _save_panel, _save_aliases,
    _save_state,
)

logger = logging.getLogger("bedcode")

VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
os.makedirs(VOICE_DIR, exist_ok=True)

SUPPORTED_DOC_EXTS = {
    ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".txt", ".md",
    ".csv", ".html", ".css", ".sh", ".bat", ".env", ".cfg", ".ini", ".xml",
}


# ── Auth ──────────────────────────────────────────────────────────
async def auth_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else None
    if not uid or (uid not in ALLOWED_USERS and uid not in READONLY_USERS):
        raise ApplicationHandlerStop()
    if update.effective_chat and not state.get("chat_id"):
        state["chat_id"] = update.effective_chat.id


def _is_readonly(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else None
    return uid is not None and uid in READONLY_USERS and uid not in ALLOWED_USERS


# ── 命令处理 ──────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    windows = await asyncio.to_thread(find_claude_windows)
    win_info = ""
    if windows:
        if not state["target_handle"]:
            state["target_handle"] = windows[0]["handle"]
        for w in windows:
            marker = " &lt;&lt; 当前" if w["handle"] == state["target_handle"] else ""
            st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(w["state"], "?")
            label_tag = f" 📌{html.escape(w['label'])}" if w.get("label") else ""
            win_info += (
                f"\n  • [{st_label}]{label_tag}{marker}"
                f"\n    handle: <code>{w['handle']}</code>"
            )
    else:
        win_info = "\n  未找到 Claude Code 窗口!"

    monitor_status = "运行中" if state.get("monitor_task") and not state["monitor_task"].done() else "未启动"
    text = (
        "<b>BedCode v6 在线</b>\n\n"
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


async def _ocr_extract(img_data: bytes) -> str:
    """Extract text from screenshot bytes via pytesseract."""
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_data))
        text = await asyncio.to_thread(pytesseract.image_to_string, img)
        return text.strip()
    except ImportError:
        return ""


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if img_data:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_data)
        # /screenshot ocr → also extract text
        if context.args and context.args[0].lower() == "ocr":
            text = await _ocr_extract(img_data)
            if text:
                await send_result(update.effective_chat.id, f"\U0001f4dd OCR:\n{text}", context)
            else:
                await update.message.reply_text("\u26a0\ufe0f pytesseract \u672a\u5b89\u88c5\u6216 OCR \u65e0\u7ed3\u679c")
    else:
        await update.message.reply_text("截屏失败")


async def cmd_ocr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Take screenshot and send OCR text only (no image)."""
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if not img_data:
        await update.message.reply_text("截屏失败")
        return
    text = await _ocr_extract(img_data)
    if text:
        await send_result(update.effective_chat.id, f"\U0001f4dd OCR:\n{text}", context)
    else:
        await update.message.reply_text("\u26a0\ufe0f pytesseract \u672a\u5b89\u88c5\u6216 OCR \u65e0\u7ed3\u679c")


async def cmd_grab(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)
    if st == "thinking":
        await update.message.reply_text("⚠️ Claude 正在思考，抓取文本可能打断！改用 /screenshot 截图")
        return
    term_text = await asyncio.to_thread(read_terminal_text, handle)
    if term_text and len(term_text.strip()) > 10:
        await send_result(update.effective_chat.id, term_text, context)
    else:
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
        _save_state()
    except ValueError:
        await update.message.reply_text("请输入数字")


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state["auto_monitor"] = not state["auto_monitor"]
    await update.message.reply_text(f"自动监控: {'开启' if state['auto_monitor'] else '关闭'}")
    _save_state()


async def cmd_autoyes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    state["auto_yes"] = not state["auto_yes"]
    await update.message.reply_text(f"自动确认: {'开启' if state['auto_yes'] else '关闭'}")
    _save_state()


async def cmd_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
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
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未锁定窗口，先 /windows")
        return
    parts = args.split()
    success = await asyncio.to_thread(send_raw_keys, handle, parts)
    if success:
        await update.message.reply_text(f"已发送: {args}")
        asyncio.create_task(_quick_screenshot(handle, update.effective_chat.id, context))
    else:
        await update.message.reply_text("按键发送失败")


async def _quick_screenshot(handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await asyncio.sleep(0.5)
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if img_data:
        try:
            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
        except Exception:
            pass


async def cmd_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    _start_monitor(handle, update.effective_chat.id, context)
    await update.message.reply_text("监控已启动")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _cancel_monitor()
    await update.message.reply_text("监控已停止")


async def cmd_break(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    success = await asyncio.to_thread(send_ctrl_c, handle)
    _cancel_monitor()
    await update.message.reply_text("⚡ Ctrl+C 已发送" if success else "❌ 发送失败")


async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from claude_detect import calc_session_cost
    info = await asyncio.to_thread(calc_session_cost)
    if not info.get("turns"):
        await update.message.reply_text("📭 暂无费用数据")
        return
    lines = [
        "💰 会话费用:",
        f"🤖 模型: {info.get('model', 'unknown')}",
        f"📊 轮次: {info['turns']}",
        f"📥 输入: {info.get('input_tokens', 0):,} tokens",
        f"📤 输出: {info.get('output_tokens', 0):,} tokens",
        f"💾 缓存读: {info.get('cache_read', 0):,} tokens",
        f"💾 缓存写: {info.get('cache_create', 0):,} tokens",
        "──────",
        f"💵 总计: ${info['cost']:.4f}",
    ]
    await update.message.reply_text("\n".join(lines))


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from claude_detect import read_last_transcript_response
    text = await asyncio.to_thread(read_last_transcript_response)
    if not text or len(text.strip()) < 10:
        await update.message.reply_text("📭 没有可导出的对话记录")
        return
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages", f"export_{int(time.time())}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    with open(filepath, "rb") as doc_file:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=doc_file,
            filename=os.path.basename(filepath),
            caption=f"📝 导出 {len(text)} 字",
        )


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到窗口，发 /windows 扫描或 /new 启动新实例")
        return
    success = await asyncio.to_thread(send_ctrl_z, handle)
    await update.message.reply_text("↩️ Ctrl+Z 已发送" if success else "❌ 发送失败")


async def cmd_windows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    windows = await asyncio.to_thread(find_claude_windows)
    if not windows:
        await update.message.reply_text("未找到 Claude Code 窗口\n用 /new 启动新实例")
        return
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
        label_tag = f" 📌{html.escape(label)}" if label else f" #{i+1}"
        lines.append(f"• [{st_label}]{label_tag}{marker}")
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
    for i, w in enumerate(windows[:3]):
        img_data = await asyncio.to_thread(capture_window_screenshot, w["handle"])
        if img_data:
            label = w.get("label", "") or f"#{i+1}"
            st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(w["state"], "?")
            await update.message.reply_photo(
                photo=img_data,
                caption=f"{label} [{st_label}]",
            )
    if len(windows) > 3:
        await update.message.reply_text(f"📸 仅显示前 3 个窗口截图（共 {len(windows)} 个）")


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    args = " ".join(context.args).strip() if context.args else ""
    if args and os.path.isdir(args):
        await update.message.reply_text(f"🚀 正在启动新实例...\n📂 {args}")
        await _launch_new_claude(update.effective_chat.id, context, args)
        return
    buttons = _build_dir_buttons()
    await update.message.reply_text(
        "📁 选择新实例的工作目录：",
        reply_markup=InlineKeyboardMarkup(buttons),
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


async def cmd_proj(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    projects = await asyncio.to_thread(_get_active_projects_detail, 8)
    handle = state["target_handle"]
    cur_title = await asyncio.to_thread(get_window_title, handle) if handle else ""
    cur_info = f"当前窗口: <code>{html.escape(cur_title[:60])}</code>" if cur_title else "未锁定窗口"
    if not projects:
        await update.message.reply_text(f"{cur_info}\n\n无最近项目", parse_mode="HTML")
        return
    buttons = []
    for p in projects:
        marker = " ✔" if cur_title and p["name"].lower() in cur_title.lower() else ""
        buttons.append([InlineKeyboardButton(f"📂 {p['name']}{marker}", callback_data=f"proj:{p['dir_name'][:56]}")])
    await update.message.reply_text(
        f"{cur_info}\n\n<b>最近项目：</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    config.SCREENSHOT_DELAY = int(os.environ.get("SCREENSHOT_DELAY", "15"))
    config.SHELL_TIMEOUT = int(os.environ.get("SHELL_TIMEOUT", "120"))
    config.WORK_DIR = os.environ.get("WORK_DIR", str(os.path.expanduser("~")))
    state["screenshot_interval"] = config.SCREENSHOT_DELAY
    state["cwd"] = config.WORK_DIR
    await update.message.reply_text(
        f"<b>配置已重载</b>\n"
        f"SCREENSHOT_DELAY={config.SCREENSHOT_DELAY}\n"
        f"SHELL_TIMEOUT={config.SHELL_TIMEOUT}\n"
        f"WORK_DIR={config.WORK_DIR}",
        parse_mode="HTML",
    )


async def cmd_tpl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        tpls = state["templates"]
        if not tpls:
            await update.message.reply_text("暂无模板\n用法: /tpl add 名称 内容")
            return
        buttons = [[InlineKeyboardButton(name, callback_data=f"tpl:{name[:59]}")] for name in tpls]
        await update.message.reply_text("📋 选择模板发送：", reply_markup=InlineKeyboardMarkup(buttons))
        return
    if args.startswith("add "):
        parts = args[4:].strip().split(None, 1)
        if len(parts) < 2:
            await update.message.reply_text("用法: /tpl add 名称 内容")
            return
        name, content = parts
        state["templates"][name] = content
        _save_templates()
        await update.message.reply_text(f"✅ 模板 <b>{html.escape(name)}</b> 已保存", parse_mode="HTML")
    elif args.startswith("del "):
        name = args[4:].strip()
        if name in state["templates"]:
            del state["templates"][name]
            _save_templates()
            await update.message.reply_text(f"🗑 模板 <b>{html.escape(name)}</b> 已删除", parse_mode="HTML")
        else:
            await update.message.reply_text(f"模板 {html.escape(name)} 不存在", parse_mode="HTML")
    else:
        await update.message.reply_text("用法: /tpl | /tpl add 名称 内容 | /tpl del 名称")


def _build_panel_markup(rows):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(b) for b in row] for row in rows],
        resize_keyboard=True, is_persistent=True,
    )


def _get_keyboard():
    return state["custom_panel"] or REPLY_KEYBOARD


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        if state["custom_panel"]:
            rows = [[b.text for b in row] for row in state["custom_panel"].keyboard]
            layout = "\n".join(f"  {' | '.join(r)}" for r in rows)
            await update.message.reply_text(f"当前自定义面板:\n{layout}\n\n/panel reset | add | del")
        else:
            await update.message.reply_text("使用默认面板\n/panel add 按钮文字\n/panel del 按钮文字\n/panel reset")
        return
    if args == "reset":
        state["custom_panel"] = None
        _save_panel(None)
        await update.message.reply_text("✅ 已恢复默认面板", reply_markup=REPLY_KEYBOARD)
        return
    if args.startswith("add "):
        btn_text = args[4:].strip()
        if not btn_text:
            await update.message.reply_text("用法: /panel add 按钮文字")
            return
        kb = state["custom_panel"] or REPLY_KEYBOARD
        rows = [[b.text for b in row] for row in kb.keyboard]
        if rows and len(rows[-1]) < 3:
            rows[-1].append(btn_text)
        else:
            rows.append([btn_text])
        state["custom_panel"] = _build_panel_markup(rows)
        _save_panel(rows)
        await update.message.reply_text(f"✅ 已添加: {btn_text}", reply_markup=state["custom_panel"])
        return
    if args.startswith("del "):
        btn_text = args[4:].strip()
        if not btn_text:
            await update.message.reply_text("用法: /panel del 按钮文字")
            return
        kb = state["custom_panel"] or REPLY_KEYBOARD
        rows = [[b for b in row if b.text != btn_text] for row in kb.keyboard]
        rows = [[b.text for b in row] for row in rows if row]
        if not rows:
            state["custom_panel"] = None
            _save_panel(None)
            await update.message.reply_text("✅ 面板已清空，恢复默认", reply_markup=REPLY_KEYBOARD)
        else:
            state["custom_panel"] = _build_panel_markup(rows)
            _save_panel(rows)
            await update.message.reply_text(f"✅ 已删除: {btn_text}", reply_markup=state["custom_panel"])
        return
    await update.message.reply_text("用法: /panel | /panel add 文字 | /panel del 文字 | /panel reset")


async def cmd_clip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if args.startswith("set "):
        if _is_readonly(update):
            await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
            return
        text = args[4:]
        ok = await asyncio.to_thread(set_clipboard_text, text)
        await update.message.reply_text("✅ 已写入剪贴板" if ok else "❌ 写入失败")
    else:
        content = await asyncio.to_thread(get_clipboard_text)
        if content:
            await send_result(update.effective_chat.id, content, context)
        else:
            await update.message.reply_text("📋 剪贴板为空")


# ── 回调处理 ──────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("target:"):
        try:
            handle = int(data.split(":")[1])
        except (ValueError, IndexError):
            await query.edit_message_text("❌ 无效的窗口句柄")
            return
        title = await asyncio.to_thread(get_window_title, handle)
        if not title:
            await query.edit_message_text("窗口已关闭，请重新 /windows")
            return
        state["target_handle"] = handle
        st = detect_claude_state(title)
        st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(st, "?")
        label = state["window_labels"].get(handle, "")
        label_tag = f" 📌{html.escape(label)}" if label else ""
        await query.edit_message_text(
            f"✅ 已切换到: [{st_label}]{label_tag}\nHandle: <code>{handle}</code>",
            parse_mode="HTML",
        )
        img_data = await asyncio.to_thread(capture_window_screenshot, handle)
        if img_data:
            await context.bot.send_photo(
                chat_id=query.message.chat_id, photo=img_data,
                caption=f"当前窗口{label_tag}",
            )

    elif data.startswith("proj:"):
        from claude_detect import _decode_proj_dirname
        dir_name = data[5:]
        proj_path = _decode_proj_dirname(dir_name)
        proj_name = dir_name.split("-")[-1] if "-" in dir_name else dir_name
        windows = await asyncio.to_thread(find_claude_windows)
        matched = None
        for w in windows:
            if proj_name.lower() in w["title"].lower():
                matched = w
                break
        if matched:
            state["target_handle"] = matched["handle"]
            st_label = {"thinking": "思考中", "idle": "空闲", "unknown": "未知"}.get(matched["state"], "?")
            await query.edit_message_text(f"✅ 已切换到 {proj_name} [{st_label}]")
            img_data = await asyncio.to_thread(capture_window_screenshot, matched["handle"])
            if img_data:
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_data)
        else:
            buttons = [[InlineKeyboardButton("🚀 启动新实例", callback_data=f"newdir:{proj_path}")]]
            await query.edit_message_text(
                f"未找到 {proj_name} 的窗口\n📂 {proj_path}",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

    elif data.startswith("label:"):
        try:
            handle = int(data.split(":")[1])
        except (ValueError, IndexError):
            await query.edit_message_text("❌ 无效的窗口句柄")
            return
        context.user_data["pending_label_handle"] = handle
        await query.edit_message_text(
            f"✏️ 请发送窗口 <code>{handle}</code> 的标签名（如项目名）：",
            parse_mode="HTML",
        )

    elif data == "break:ctrlc":
        handle = state.get("target_handle")
        if handle:
            success = await asyncio.to_thread(send_ctrl_c, handle)
            await query.edit_message_text("⚡ Ctrl+C 已发送" if success else "❌ 发送失败")
        else:
            await query.edit_message_text("❌ 无目标窗口")

    elif data.startswith("qr:"):
        keys = data[3:]
        handle = await _get_handle()
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
        async with _queue_lock:
            items = list(state["msg_queue"])
        if not items:
            await query.edit_message_text("📋 队列为空")
            return
        queue_list = "\n".join(
            f"{i+1}. {msg[:80]}{'...' if len(msg) > 80 else ''}"
            for i, msg in enumerate(items)
        )
        del_buttons = [
            [InlineKeyboardButton(f"🗑 删除第{i+1}条", callback_data=f"queue:del:{i}")]
            for i in range(min(len(items), 5))
        ]
        del_buttons.append([InlineKeyboardButton("🗑 清空全部", callback_data="queue:clear")])
        await query.edit_message_text(
            f"📋 当前队列 ({len(items)} 条):\n\n{queue_list}",
            reply_markup=InlineKeyboardMarkup(del_buttons),
        )

    elif data == "queue:clear":
        async with _queue_lock:
            count = len(state["msg_queue"])
            state["msg_queue"].clear()
        await query.edit_message_text(f"🗑 已清空队列 ({count} 条消息)")

    elif data == "new_claude":
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
        handle = await _get_handle()
        if handle:
            img_data = await asyncio.to_thread(capture_window_screenshot, handle)
            if img_data:
                try:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_data)
                except Exception:
                    pass

    elif data.startswith("retry:"):
        action = data.split(":")[1]
        handle = await _get_handle()
        if not handle:
            await query.edit_message_text("❌ 窗口已关闭")
            return
        retry_text = {"again": "请重试上一个操作", "alt": "请换一种方案重新实现"}.get(action, "请重试")
        await query.edit_message_text(f"🔄 已发送: {retry_text}")
        success = await asyncio.to_thread(send_keys_to_window, handle, retry_text)
        if success and state["auto_monitor"]:
            _start_monitor(handle, query.message.chat_id, context)

    elif data.startswith("queue:del:"):
        try:
            idx = int(data.split(":")[2])
            async with _queue_lock:
                q = list(state["msg_queue"])
                if 0 <= idx < len(q):
                    del q[idx]
                    state["msg_queue"].clear()
                    for m in q:
                        state["msg_queue"].append(m)
                    deleted = True
                else:
                    deleted = False
            if deleted:
                await query.edit_message_text(f"🗑 已删除第 {idx+1} 条，剩余 {len(q)} 条")
            else:
                await query.edit_message_text("❌ 索引无效")
        except (ValueError, IndexError):
            await query.edit_message_text("❌ 无效操作")

    elif data.startswith("resend:"):
        try:
            idx = int(data.split(":")[1])
            history = list(state["cmd_history"])
            if 0 <= idx < len(history):
                text = history[idx]
                await query.edit_message_text(f"🔁 重发: {text[:80]}")
                state["cmd_history"].append(text)
                await _inject_to_claude(update, context, text)
            else:
                await query.edit_message_text("❌ 历史记录已过期")
        except (ValueError, IndexError):
            await query.edit_message_text("❌ 无效的历史索引")

    elif data.startswith("tpl:"):
        name = data[4:]
        content = state["templates"].get(name)
        if not content:
            await query.edit_message_text(f"模板 {name} 不存在")
            return
        await query.edit_message_text(f"📋 发送模板: {name}")
        state["cmd_history"].append(content)
        await _inject_to_claude(update, context, content)


# ── 启动新实例 ────────────────────────────────────────────────────
async def _launch_new_claude(chat_id: int, context: ContextTypes.DEFAULT_TYPE, work_dir: str = None, new_window: bool = False) -> None:
    if work_dir is None:
        work_dir = state["cwd"]
    _save_recent_dir(work_dir)
    try:
        wt_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe")
        git_bash = os.environ.get("GIT_BASH_PATH", GIT_BASH_PATH)
        bat_path = os.path.join(tempfile.gettempdir(), "bedcode_launch.bat")
        safe_dir = work_dir.replace('"', '')
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(f"@set CLAUDE_CODE_GIT_BASH_PATH={git_bash}\n")
            f.write(f"@cd /d \"{safe_dir}\"\n")
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
            text="❌ 启动失败，详见日志",
        )


# ── 消息处理 ──────────────────────────────────────────────────────
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    photo = update.message.photo[-1]
    caption = (update.message.caption or "").strip()
    file = await context.bot.get_file(photo.file_id)
    ts = int(time.time())
    filename = f"tg_{ts}_{photo.file_unique_id}.jpg"
    filepath = os.path.join(IMG_DIR, filename)
    await file.download_to_drive(filepath)
    logger.info(f"图片已保存: {filepath}")

    handle = await _get_handle()

    # 尝试 Alt+V 粘贴图片到 Claude Code 窗口
    if handle and not state.get("stream_mode"):
        copied = await asyncio.to_thread(copy_image_to_clipboard, filepath)
        if copied:
            pasted = await asyncio.to_thread(paste_image_to_window, handle)
            if pasted:
                await update.message.reply_text("🖼 图片已通过 Alt+V 粘贴")
                if caption:
                    # 有 caption：输入文字并回车
                    await asyncio.to_thread(send_keys_to_window, handle, caption)
                else:
                    # 无 caption：直接回车提交图片
                    await asyncio.to_thread(send_keys_to_window, handle, "请分析这个图片")
                if state["auto_monitor"]:
                    _start_monitor(handle, update.effective_chat.id, context)
                return

    # 降级：路径注入
    inject_text = f"{caption} {filepath}" if caption else f"请分析这个图片 {filepath}"
    await _inject_to_claude(update, context, inject_text, skip_file_check=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return
    state["last_tg_msg_time"] = time.time()

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

    # Alias expansion
    aliases = state.get("aliases", {})
    if aliases and text in aliases:
        text = aliases[text]

    BUTTON_MAP = {
        "📷 截屏": cmd_screenshot,
        "🪟 窗口": cmd_windows,
        "🆕 新实例": cmd_new,
        "👀 监控": cmd_watch,
        "⏹ 停止": cmd_stop,
        "🔄 状态": cmd_start,
    }
    if text in BUTTON_MAP:
        await BUTTON_MAP[text](update, context)
        return

    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return

    # Custom panel buttons: if text matches a custom button not in BUTTON_MAP, inject as text
    if state["custom_panel"]:
        custom_btns = {b.text for row in state["custom_panel"].keyboard for b in row}
        if text in custom_btns:
            state["cmd_history"].append(text)
            await _inject_to_claude(update, context, text)
            return

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

    if state["stream_mode"]:
        state["cmd_history"].append(text)
        await _stream_send(text, update.effective_chat.id, context)
        return

    state["cmd_history"].append(text)
    await _inject_to_claude(update, context, text)


async def _inject_to_claude(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, skip_file_check: bool = False) -> None:
    handle = await _get_handle()
    if not handle:
        await update.message.reply_text("未找到 Claude Code 窗口!\n请先启动 Claude Code，然后 /windows")
        return

    inject_text = text
    if not skip_file_check and _needs_file(text):
        filepath = _save_msg_file(text)
        inject_text = f"请阅读这个文件并按其中的指示操作 {filepath}"
        logger.info(f"长消息保存为文件: {filepath}")

    title = await asyncio.to_thread(get_window_title, handle)
    st = detect_claude_state(title)

    if st == "thinking":
        async with _queue_lock:
            if len(state["msg_queue"]) >= 50:
                await update.message.reply_text("⚠️ 队列已满 (50条)，请等待 Claude 完成")
                return
            state["msg_queue"].append(inject_text)
            state["queue_chat_id"] = update.effective_chat.id
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
        if not state.get("monitor_task") or state["monitor_task"].done():
            _start_monitor(handle, update.effective_chat.id, context)
        return

    logger.info(f"注入到窗口 {handle}: {inject_text[:80]}")
    success = await asyncio.to_thread(send_keys_to_window, handle, inject_text)

    if not success:
        handle = await _get_handle()
        if handle:
            success = await asyncio.to_thread(send_keys_to_window, handle, inject_text)
        if not success:
            _cancel_monitor()
            state["target_handle"] = None
            await _update_status(update.effective_chat.id, "❌ 发送失败，窗口可能已关闭\n发 /windows 重新扫描", context)
            return

    await _update_status(update.effective_chat.id, "✅ 已发送", context)

    if state["auto_monitor"]:
        _start_monitor(handle, update.effective_chat.id, context)


async def _run_shell(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd: str) -> None:
    DANGEROUS_PATTERNS = {"rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){ :|:&", "fork bomb", "> /dev/sd", "chmod -R 777 /", "chown -R", "> /dev/null 2>&1 &"}
    cmd_lower = cmd.lower().strip()
    if any(p in cmd_lower for p in DANGEROUS_PATTERNS):
        await update.message.reply_text("⚠️ 危险命令已拦截")
        return
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
        logger.exception(f"Shell 命令执行失败: {e}")
        await thinking.edit_text("❌ 执行出错，详见日志")


# ── 语音消息处理 ──────────────────────────────────────────────────
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    ts = int(time.time())
    filename = f"voice_{ts}_{voice.file_unique_id}.ogg"
    filepath = os.path.join(VOICE_DIR, filename)
    await file.download_to_drive(filepath)
    logger.info(f"语音已保存: {filepath}")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            from openai import OpenAI
            import io as _io
            client = OpenAI(api_key=api_key)
            audio_bytes = await asyncio.to_thread(lambda: open(filepath, "rb").read())
            transcription = await asyncio.to_thread(
                lambda: client.audio.transcriptions.create(model="whisper-1", file=("audio.ogg", _io.BytesIO(audio_bytes)))
            )
            text = transcription.text.strip()
            await update.message.reply_text(f"🎤 识别结果: {text}")
            state["cmd_history"].append(text)
            await _inject_to_claude(update, context, text)
        except Exception as e:
            logger.exception(f"Whisper 转写失败: {e}")
            await update.message.reply_text("⚠️ 语音转写失败，详见日志")
            inject_text = f"用户发送了语音消息，文件路径: {filepath}"
            await _inject_to_claude(update, context, inject_text, skip_file_check=True)
    else:
        await update.message.reply_text("⚠️ 未配置 OPENAI_API_KEY，语音转文字不可用")
        inject_text = f"用户发送了语音消息，文件路径: {filepath}"
        await _inject_to_claude(update, context, inject_text, skip_file_check=True)


# ── 文件/文档处理 ─────────────────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_readonly(update):
        await update.message.reply_text("\ud83d\udd12 只读用户无此权限")
        return
    doc = update.message.document
    ext = os.path.splitext(doc.file_name or "")[1].lower()
    if ext not in SUPPORTED_DOC_EXTS:
        await update.message.reply_text(f"⚠️ 不支持的文件类型: {ext}")
        return
    if doc.file_size and doc.file_size > 10 * 1024 * 1024:
        await update.message.reply_text("⚠️ 文件过大 (>10MB)")
        return
    file = await context.bot.get_file(doc.file_id)
    safe_name = pathlib.Path(doc.file_name or "upload").name.strip() or "upload"
    if ".." in safe_name:
        safe_name = "upload"
    filepath = os.path.join(state["cwd"], safe_name)
    await file.download_to_drive(filepath)
    logger.info(f"文件已保存: {filepath}")
    caption = (update.message.caption or "").strip() or "请查看这个文件"
    await update.message.reply_text(f"📄 文件已保存: {doc.file_name}")
    await _inject_to_claude(update, context, f"{caption} {filepath}", skip_file_check=True)


# ── 命令历史 ─────────────────────────────────────────────────────
async def cmd_diff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        result = await asyncio.to_thread(
            lambda: subprocess.run(
                [GIT_BASH_PATH, "-c", "git diff --stat HEAD~1"],
                capture_output=True, text=True, timeout=30, cwd=state["cwd"],
            )
        )
        if result.returncode != 0:
            await update.message.reply_text("当前目录不是 Git 仓库或无提交历史")
            return
        output = result.stdout.strip()
        if not output:
            await update.message.reply_text("无变更")
            return
        full = await asyncio.to_thread(
            lambda: subprocess.run(
                [GIT_BASH_PATH, "-c", "git diff HEAD~1"],
                capture_output=True, text=True, timeout=30, cwd=state["cwd"],
            )
        )
        await send_result(update.effective_chat.id, f"{output}\n\n{full.stdout}", context)
    except Exception as e:
        await update.message.reply_text(f"执行失败: {e}")


async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    n = min(int(args), 100) if args.isdigit() else 30
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail = "".join(lines[-n:])
        await send_result(update.effective_chat.id, tail or "(日志为空)", context)
    except FileNotFoundError:
        await update.message.reply_text("日志文件不存在")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyword = " ".join(context.args).strip() if context.args else ""
    if not keyword:
        await update.message.reply_text("用法: /search 关键词")
        return
    history = list(state["cmd_history"])
    matches = [(i, msg) for i, msg in enumerate(history) if keyword.lower() in msg.lower()]
    if not matches:
        await update.message.reply_text(f"未找到包含「{html.escape(keyword)}」的记录", parse_mode="HTML")
        return
    lines = []
    buttons = []
    for i, msg in matches:
        lines.append(f"{i+1}. {html.escape(msg[:60])}")
        buttons.append([InlineKeyboardButton(
            f"{i+1}. {msg[:40]}{'...' if len(msg) > 40 else ''}",
            callback_data=f"resend:{i}",
        )])
    await update.message.reply_text(
        f"🔍 搜索「{html.escape(keyword)}」({len(matches)} 条)：\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )



async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        await update.message.reply_text(
            "用法:\n<code>/schedule 30m 请检查进度</code>\n"
            "<code>/schedule list</code> 查看任务\n<code>/schedule clear</code> 清空任务\n"
            "时间格式: 10s / 5m / 1h", parse_mode="HTML",
        )
        return
    if args == "list":
        tasks = [t for t in state["scheduled_tasks"] if not t["task"].done()]
        state["scheduled_tasks"] = tasks
        if not tasks:
            await update.message.reply_text("无待执行的定时任务")
            return
        import datetime
        lines = [f"{i+1}. [{datetime.datetime.fromtimestamp(t['fire_at']).strftime('%H:%M:%S')}] {t['text'][:50]}" for i, t in enumerate(tasks)]
        await update.message.reply_text("\n".join(lines))
        return
    if args == "clear":
        for t in state["scheduled_tasks"]:
            if not t["task"].done():
                t["task"].cancel()
        count = len(state["scheduled_tasks"])
        state["scheduled_tasks"] = []
        await update.message.reply_text(f"已清空 {count} 个定时任务")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("格式: /schedule 时间 消息内容")
        return
    time_str, text = parts
    if not time_str or time_str[-1] not in "smh":
        await update.message.reply_text("无效时间格式，示例: 10s / 5m / 1h")
        return
    multiplier = {"s": 1, "m": 60, "h": 3600}[time_str[-1]]
    try:
        val = int(time_str[:-1])
    except ValueError:
        val = 0
    if not multiplier or val <= 0 or val > 720:
        await update.message.reply_text("无效时间格式，示例: 10s / 5m / 1h")
        return
    delay = val * multiplier
    fire_at = time.time() + delay
    chat_id = update.effective_chat.id

    async def _scheduled_send():
        try:
            await asyncio.sleep(delay)
            handle = await _get_handle()
            if handle:
                await asyncio.to_thread(send_keys_to_window, handle, text)
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"⏰ 定时消息已发送: {text[:80]}")
                except Exception:
                    pass
                if state["auto_monitor"]:
                    _start_monitor(handle, chat_id, context)
        finally:
            state["scheduled_tasks"] = [t for t in state["scheduled_tasks"] if not t["task"].done()]

    task = asyncio.create_task(_scheduled_send())
    state["scheduled_tasks"].append({"text": text, "fire_at": fire_at, "task": task})
    await update.message.reply_text(f"⏰ 已设定: {time_str} 后发送\n内容: {text[:80]}")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history = list(state["cmd_history"])
    if not history:
        await update.message.reply_text("📜 暂无历史记录")
        return
    lines = []
    buttons = []
    for i, msg in enumerate(history):
        lines.append(f"{i+1}. {html.escape(msg[:60])}{'...' if len(msg) > 60 else ''}")
        buttons.append([InlineKeyboardButton(
            f"{i+1}. {msg[:40]}{'...' if len(msg) > 40 else ''}",
            callback_data=f"resend:{i}",
        )])
    await update.message.reply_text(
        f"📜 最近 {len(history)} 条消息：\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_quiet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        qs, qe = state.get("quiet_start"), state.get("quiet_end")
        if qs is not None and qe is not None:
            await update.message.reply_text(f"免打扰: {qs}:00 - {qe}:00\n/quiet off 关闭")
        else:
            await update.message.reply_text("免打扰: 关闭\n用法: /quiet 23-8")
        return
    if args == "off":
        state["quiet_start"] = None
        state["quiet_end"] = None
        await update.message.reply_text("免打扰已关闭")
        _save_state()
        return
    try:
        s, e = args.split("-")
        qs, qe = int(s), int(e)
        if not (0 <= qs <= 23 and 0 <= qe <= 23):
            raise ValueError
    except (ValueError, TypeError):
        await update.message.reply_text("格式: /quiet 23-8 (小时 0-23)")
        return
    state["quiet_start"] = qs
    state["quiet_end"] = qe
    await update.message.reply_text(f"免打扰已设置: {qs}:00 - {qe}:00")
    _save_state()


async def cmd_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        aliases = state.get("aliases", {})
        if not aliases:
            await update.message.reply_text("暂无别名\n用法: /alias ss screenshot")
            return
        lines = [f"/{k} → /{v}" for k, v in aliases.items()]
        await update.message.reply_text("别名列表:\n" + "\n".join(lines))
        return
    if args.startswith("del "):
        name = args[4:].strip()
        if name in state.get("aliases", {}):
            del state["aliases"][name]
            _save_aliases()
            await update.message.reply_text(f"已删除别名: {name}")
        else:
            await update.message.reply_text(f"别名 {name} 不存在")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        await update.message.reply_text("用法: /alias 别名 命令\n例: /alias ss screenshot")
        return
    name, target = parts
    state["aliases"][name] = target
    _save_aliases()
    await update.message.reply_text(f"已创建别名: /{name} → /{target}")


async def cmd_batch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args or "|" not in args:
        await update.message.reply_text("用法: /batch msg1 | msg2 | msg3")
        return
    msgs = [m.strip() for m in args.split("|") if m.strip()]
    if not msgs:
        await update.message.reply_text("没有有效消息")
        return
    async with _queue_lock:
        space = 50 - len(state["msg_queue"])
        if space <= 0:
            await update.message.reply_text("⚠️ 队列已满 (50条)")
            return
        added = msgs[:space]
        for m in added:
            state["msg_queue"].append(m)
    if len(added) < len(msgs):
        await update.message.reply_text(f"📋 已加入 {len(added)} 条，{len(msgs)-len(added)} 条因队列满被丢弃")
    else:
        await update.message.reply_text(f"📋 已加入队列 {len(added)} 条消息")


async def cmd_tts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = " ".join(context.args).strip() if context.args else ""
    if not args:
        from claude_detect import read_last_transcript_response
        args = await asyncio.to_thread(read_last_transcript_response)
    if not args or len(args.strip()) < 5:
        await update.message.reply_text("无内容可转语音")
        return
    text = args[:2000]
    try:
        import edge_tts
        tts = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
        outfile = os.path.join(VOICE_DIR, f"tts_{int(time.time())}.mp3")
        await tts.save(outfile)
        with open(outfile, "rb") as f:
            await context.bot.send_voice(chat_id=update.effective_chat.id, voice=f)
    except ImportError:
        await update.message.reply_text("⚠️ edge-tts 未安装: pip install edge-tts")
    except Exception as e:
        await update.message.reply_text(f"TTS 失败: {e}")
