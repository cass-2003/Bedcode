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
    send_keys_to_window,
)
from claude_detect import detect_claude_state, read_terminal_text, read_last_transcript_response
from utils import send_result

logger = logging.getLogger("bedcode")


def _fmt_elapsed(start: float) -> str:
    s = int(time.time() - start)
    return f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


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


async def _update_status(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = state.get("status_msg")
    if msg:
        try:
            await msg.edit_text(text)
            return
        except Exception:
            pass
    try:
        state["status_msg"] = await context.bot.send_message(
            chat_id=chat_id, text=text
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


async def _monitor_loop(
    handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    interval = state["screenshot_interval"]
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
            await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)})", context)

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
                    await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)})", context)
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
                if last_state != "thinking":
                    queue_text = ""
                    if state["msg_queue"]:
                        items = list(state["msg_queue"])
                        shown = [f"[{i+1}]{m[:20]}" for i, m in enumerate(items[:5])]
                        extra = len(items) - 5
                        queue_text = "\n📋 " + " → ".join(shown)
                        if extra > 0:
                            queue_text += f" ... 还有 {extra} 条"
                    await _update_status(chat_id, f"⏳ Claude 思考中... ({_fmt_elapsed(start_time)}){queue_text}", context)
                last_state = st

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

                    state["last_screenshot_hash"] = None
                    img_data = await asyncio.to_thread(capture_window_screenshot, handle)
                    if img_data:
                        try:
                            await context.bot.send_photo(chat_id=chat_id, photo=img_data)
                        except Exception:
                            pass

                    term_text = await asyncio.to_thread(read_last_transcript_response)
                    if not term_text or len(term_text.strip()) <= 10:
                        term_text = await asyncio.to_thread(read_terminal_text, handle)
                    if term_text and len(term_text.strip()) > 10:
                        await send_result(chat_id, term_text, context)

                    if state["msg_queue"]:
                        next_msg = state["msg_queue"].popleft()
                        remaining = len(state["msg_queue"])
                        queue_text = ""
                        if remaining > 0:
                            items = list(state["msg_queue"])
                            shown = [f"[{i+1}]{m[:20]}" for i, m in enumerate(items[:5])]
                            extra = remaining - 5
                            queue_text = "\n📋 " + " → ".join(shown)
                            if extra > 0:
                                queue_text += f" ... 还有 {extra} 条"
                        try:
                            state["status_msg"] = await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"📤 发送队列消息:\n{next_msg[:100]}{queue_text}",
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
    task = state.get("monitor_task")
    if task and not task.done():
        task.cancel()
    state["monitor_task"] = None


def _start_monitor(handle: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    _cancel_monitor()
    state["monitor_task"] = asyncio.create_task(
        _monitor_loop(handle, chat_id, context)
    )
