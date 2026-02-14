"""监控循环: 交互提示检测、状态消息管理。"""
import re
import html
import time
import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import state
from win32_api import (
    capture_window_screenshot, _image_hash, get_window_title,
    send_keys_to_window, send_raw_keys,
)
from claude_detect import detect_claude_state, read_terminal_text, read_last_transcript_response, find_claude_windows
from utils import send_result

logger = logging.getLogger("bedcode")
_queue_lock = asyncio.Lock()


def _fmt_elapsed(start: float) -> str:
    s = int(time.time() - start)
    return f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


def _build_queue_text() -> str:
    if not state["msg_queue"]:
        return ""
    items = list(state["msg_queue"])
    shown = [f"[{i+1}]{m[:20]}" for i, m in enumerate(items[:5])]
    extra = len(items) - 5
    text = "\n📋 " + " → ".join(shown)
    if extra > 0:
        text += f" ... 还有 {extra} 条"
    return text


def _detect_interactive_prompt(text: str) -> str | None:
    if not text:
        return None
    lines = text.strip().split("\n")
    tail = "\n".join(lines[-30:])
    prompts = [
        "Select an option", "Choose", "approve", "deny", "Yes",
        "allowedPrompts", "Do you want", "(y/n)", "(Y/n)",
        "❯", "◯", "◉", "☐", "☑",
    ]
    for p in prompts:
        if p in tail:
            return tail
    return None


def _parse_prompt_type(prompt_text: str) -> list[tuple[str, str]]:
    lower = prompt_text.lower()
    if "(y/n)" in lower or "(y/n)?" in lower or "yes/no" in lower:
        return [("✅ Yes", "y enter"), ("❌ No", "n enter")]
    if "❯" in prompt_text:
        return [("↑", "up"), ("↓", "down"), ("✓ 确认", "enter")]
    numbered = re.findall(r'(?:^|\n)\s*[\[\(]?(\d+)[\]\)]', prompt_text)
    if numbered:
        nums = sorted(set(int(n) for n in numbered if 0 < int(n) <= 9))
        if nums:
            return [(f"{n}", f"{n} enter") for n in nums]
    return []


_BREAK_MARKUP = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Ctrl+C", callback_data="break:ctrlc")]])


async def _update_status(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE, markup=None) -> None:
    msg = state.get("status_msg")
    if msg:
        try:
            await msg.edit_text(text, reply_markup=markup)
            return
        except Exception:
            pass
    try:
        state["status_msg"] = await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=markup
        )
    except Exception:
        pass


async def _delete_status() -> None:
    msg = state.get("status_msg")
    if msg:
        try:
            await msg.delete()
        except Exception:
            pass
        state["status_msg"] = None


async def _forward_result(chat_id: int, handle: int, ctx) -> None:
    """截图+文本转发到 Telegram。ctx 可以是 ContextTypes 或 Application。"""
    bot = ctx.bot if hasattr(ctx, 'bot') else ctx
    state["last_screenshot_hash"] = None
    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
    if img_data:
        for _attempt in range(2):
            try:
                await bot.send_photo(chat_id=chat_id, photo=img_data)
                break
            except Exception:
                if _attempt == 0:
                    await asyncio.sleep(1)
    term_text = await asyncio.to_thread(read_last_transcript_response)
    if not term_text or len(term_text.strip()) <= 10:
        term_text = await asyncio.to_thread(read_terminal_text, handle)
    if term_text and len(term_text.strip()) > 10:
        # Detect notification level
        _err_kw = ("error", "Error", "failed", "Failed", "❌", "traceback", "Traceback", "exception", "Exception")
        _ok_kw = ("✅", "完成", "done", "success", "passed")
        if any(k in term_text for k in _err_kw):
            level = "error"
        elif any(k in term_text for k in _ok_kw):
            level = "success"
        else:
            level = "info"

        prefix = {"error": "🚨 ", "success": "✅ "}.get(level, "")
        # Add project label for multi-window identification
        win_title = await asyncio.to_thread(get_window_title, handle)
        if win_title:
            proj_label = win_title.lstrip(''.join('⠂⠃⠄⠆⠇⠋⠙⠸⠴⠤✳ ')).strip()
            if proj_label:
                term_text = f"📂 {proj_label}\n\n{term_text}"
        await send_result(chat_id, prefix + term_text if prefix else term_text, ctx)

        if level == "error":
            await bot.send_message(chat_id=chat_id, text="🚨 检测到错误输出，请检查！")


async def _monitor_loop(
    handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    max_duration = 3600
    start_time = time.time()
    last_screenshot_time = 0
    was_thinking = False
    idle_count = 0
    last_state = None
    grace_period = 5

    try:
        title = await asyncio.to_thread(get_window_title, handle)
        st = detect_claude_state(title)
        if st == "thinking":
            was_thinking = True
            last_state = "thinking"
            grace_period = 0
            await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)})", context, markup=_BREAK_MARKUP)

        while True:
            await asyncio.sleep(1.5)

            if time.time() - start_time > max_duration:
                await _update_status(chat_id, "⏰ 监控超时 (60分钟)，已自动停止", context)
                break

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
                    await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)})", context, markup=_BREAK_MARKUP)
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

            title = await asyncio.to_thread(get_window_title, handle)
            if not title:
                break

            st = detect_claude_state(title)
            logger.info(f"监控状态: title={title[:30]!r} state={st} was_thinking={was_thinking} idle_count={idle_count}")

            if st == "thinking":
                was_thinking = True
                idle_count = 0
                await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)}){_build_queue_text()}", context, markup=_BREAK_MARKUP)
                last_state = st

                # 思考超时自动截图: ~30s, ~90s, ~180s
                elapsed = int(time.time() - start_time)
                if elapsed in range(30, 32) or elapsed in range(90, 92) or elapsed in range(180, 182):
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data, caption=f"⏳ 思考已 {_fmt_elapsed(start_time)}")
                        except Exception:
                            pass

                text = await asyncio.to_thread(read_terminal_text, handle)
                prompt = _detect_interactive_prompt(text) if text else None
                if prompt:
                    logger.info(f"[监控] thinking 状态下检测到交互提示")
                    # autoyes: 自动回复 y/n 提示
                    if state.get("auto_yes") and _parse_prompt_type(prompt):
                        parsed = _parse_prompt_type(prompt)
                        if parsed and parsed[0][0] == "✅ Yes":
                            keys = parsed[0][1].split()
                            await asyncio.to_thread(send_raw_keys, handle, keys)
                            logger.info("[监控] autoyes: 自动回复 y")
                            await context.bot.send_message(chat_id=chat_id, text="🤖 autoyes: 自动确认 y")
                            was_thinking = False
                            idle_count = 0
                            grace_period = 5
                            continue
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass
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
                if idle_count >= 2:
                    title_recheck = await asyncio.to_thread(get_window_title, handle)
                    st_recheck = detect_claude_state(title_recheck)
                    if st_recheck == "thinking":
                        logger.info(f"[监控] idle 确认后又变为 thinking，继续监控")
                        was_thinking = True
                        idle_count = 0
                        last_state = "thinking"
                        await _update_status(chat_id, f"⏳ Claude 继续执行中... ({_fmt_elapsed(start_time)})", context)
                        continue

                    await _delete_status()

                    await _forward_result(chat_id, handle, context)

                    if state.get("auto_pin", True):
                        try:
                            pin_msg = await context.bot.send_message(chat_id=chat_id, text="\ud83d\udccc Claude \u5b8c\u6210")
                            await context.bot.pin_chat_message(chat_id=chat_id, message_id=pin_msg.message_id, disable_notification=True)
                        except Exception:
                            pass

                    async with _queue_lock:
                        has_queued = bool(state["msg_queue"])
                        next_msg = state["msg_queue"].popleft() if has_queued else None
                    if next_msg is not None:
                        try:
                            state["status_msg"] = await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"📤 发送队列消息:\n{next_msg[:100]}{_build_queue_text()}",
                            )
                        except Exception:
                            pass
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
                        was_thinking = False
                        idle_count = 0
                        last_state = None
                        grace_period = 5
                    else:
                        buttons = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("🔄 重试", callback_data="retry:again"),
                                InlineKeyboardButton("🔀 换方案", callback_data="retry:alt"),
                            ],
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

            now = time.time()
            if now - last_screenshot_time >= state["screenshot_interval"]:
                last_screenshot_time = now
                img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                if img_data:
                    img_hash = _image_hash(img_data)
                    if img_hash != state["last_screenshot_hash"]:
                        state["last_screenshot_hash"] = img_hash
                        for _attempt in range(2):
                            try:
                                await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                                break
                            except Exception:
                                if _attempt == 0:
                                    await asyncio.sleep(1)

    except asyncio.CancelledError:
        await _delete_status()
    except Exception as e:
        logger.error(f"监控循环异常: {e}")
        try:
            await context.bot.send_message(chat_id=state.get("chat_id"), text="⚠️ 监控异常已停止，请检查日志")
        except Exception:
            pass


def _cancel_monitor():
    task = state.get("monitor_task")
    if task and not task.done():
        task.cancel()
    state["monitor_task"] = None


def _start_monitor(handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    _cancel_monitor()
    state["monitor_task"] = asyncio.create_task(
        _monitor_loop(handle, chat_id, context)
    )


async def _passive_monitor_loop(app) -> None:
    """常驻后台监控：检测所有 Claude 窗口的 thinking→idle 转换，自动转发结果到 Telegram。"""
    window_states = {}  # handle → {"was_thinking", "idle_count", "think_start", "status_msg"}

    while True:
        try:
            await asyncio.sleep(2)

            chat_id = state.get("chat_id")
            if not chat_id:
                continue

            # 如果 Telegram 触发的监控正在运行，让它处理，被动监控跳过
            active_task = state.get("monitor_task")
            if active_task and not active_task.done():
                for ws in window_states.values():
                    if ws["status_msg"]:
                        try: await ws["status_msg"].delete()
                        except Exception: pass
                window_states.clear()
                was_thinking = False
                thinking_start = None
                passive_status_msg = None
                continue

            windows = await asyncio.to_thread(find_claude_windows)
            live_handles = {w["handle"] for w in windows}

            # Clean up entries for windows that no longer exist
            for h in list(window_states):
                if h not in live_handles:
                    ws = window_states.pop(h)
                    if ws["status_msg"]:
                        try: await ws["status_msg"].delete()
                        except Exception: pass

            # Auto-update target_handle if current one is gone
            if state.get("target_handle") not in live_handles:
                if windows:
                    state["target_handle"] = windows[0]["handle"]
                    logger.info(f"[被动监控] 窗口已关闭，自动切换到 {windows[0]['handle']}")
                else:
                    state["target_handle"] = None
                    continue

            for w_info in windows:
                handle = w_info["handle"]
                label = w_info.get("label") or f"窗口{handle}"
                st = w_info["state"]

                if handle not in window_states:
                    window_states[handle] = {
                        "was_thinking": False, "idle_count": 0,
                        "think_start": None, "status_msg": None,
                    }
                ws = window_states[handle]

                if st == "thinking":
                    ws["idle_count"] = 0
                    if not ws["was_thinking"]:
                        ws["was_thinking"] = True
                        ws["think_start"] = time.time()
                        try:
                            ws["status_msg"] = await app.bot.send_message(
                                chat_id=chat_id, text=f"🧠 [{label}] 思考中... (0s)")
                        except Exception:
                            ws["status_msg"] = None
                    elif ws["status_msg"] and ws["think_start"]:
                        try:
                            await ws["status_msg"].edit_text(
                                f"🧠 [{label}] 思考中... ({_fmt_elapsed(ws['think_start'])})")
                        except Exception:
                            pass

                elif st == "idle" and ws["was_thinking"]:
                    ws["idle_count"] += 1
                    if ws["idle_count"] >= 2:
                        # 再次确认
                        title2 = await asyncio.to_thread(get_window_title, handle)
                        if title2 and detect_claude_state(title2) == "thinking":
                            ws["idle_count"] = 0
                            continue

                        # 删除思考状态消息
                        if ws["status_msg"]:
                            try: await ws["status_msg"].delete()
                            except Exception: pass
                            ws["status_msg"] = None
                            ws["think_start"] = None

                        logger.info(f"[被动监控] [{label}] 检测到完成，转发结果")

                        # Check quiet hours
                        qs, qe = state.get("quiet_start"), state.get("quiet_end")
                        if qs is not None and qe is not None:
                            hour = time.localtime().tm_hour
                            in_quiet = (hour >= qs or hour < qe) if qs > qe else (qs <= hour < qe)
                            if in_quiet:
                                ws["was_thinking"] = False; ws["idle_count"] = 0; continue

                        # 智能通知: 5分钟内没有 TG 消息则静默（用户在电脑前）
                        if time.time() - state.get("last_tg_msg_time", 0) > 300:
                            logger.info("[被动监控] 用户不在 TG，静默跳过")
                            ws["was_thinking"] = False; ws["idle_count"] = 0; continue

                        await app.bot.send_message(chat_id=chat_id, text=f"📌{label} 完成")
                        await _forward_result(chat_id, handle, app)

                        ws["was_thinking"] = False
                        ws["idle_count"] = 0
                else:
                    ws["idle_count"] = 0

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"被动监控异常: {e}")
            await asyncio.sleep(5)


def _start_passive_monitor(app):
    task = state.get("passive_monitor_task")
    if task and not task.done():
        return
    state["passive_monitor_task"] = asyncio.create_task(
        _passive_monitor_loop(app)
    )
