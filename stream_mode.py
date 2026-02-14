"""流式模式: Git Bash 检测、子进程管理、流式读取。"""
import os
import json
import html
import time
import asyncio
import subprocess
import logging

from telegram.ext import ContextTypes

from config import state
from utils import split_text
from monitor import _update_status, _delete_status

logger = logging.getLogger("bedcode")


def _find_git_bash() -> str:
    env_path = os.environ.get("GIT_BASH_PATH", "")
    if env_path and os.path.isfile(env_path):
        return env_path
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    try:
        result = subprocess.run(
            ["where", "bash"], capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            if "git" in line.lower() and os.path.isfile(line.strip()):
                return line.strip()
    except Exception:
        pass
    logger.warning("未找到 Git Bash，使用默认路径")
    return r"C:\Program Files\Git\bin\bash.exe"


GIT_BASH_PATH = _find_git_bash()
logger.info(f"Git Bash: {GIT_BASH_PATH}")


def _kill_stream_proc():
    proc = state.get("stream_proc")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    state["stream_proc"] = None
    task = state.get("stream_task")
    if task and not task.done():
        task.cancel()
    state["stream_task"] = None


async def _stream_reader(proc, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    loop = asyncio.get_event_loop()
    buf = ""
    last_flush = time.time()
    notified_thinking = False
    line_count = 0

    logger.info(f"[流式] reader 启动, PID={proc.pid}")

    try:
        while True:
            try:
                line_bytes = await asyncio.wait_for(
                    loop.run_in_executor(None, proc.stdout.readline), timeout=30
                )
            except asyncio.TimeoutError:
                logger.error("[流式] stdout readline 超时 (30s)，终止读取")
                break
            except Exception as e:
                logger.error(f"[流式] stdout 读取异常: {e}")
                break
            if not line_bytes:
                logger.info(f"[流式] stdout EOF, 共读取 {line_count} 行")
                try:
                    stderr_out = await loop.run_in_executor(None, proc.stderr.read)
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
                        await _update_status(chat_id, f"🔧 调用工具: {tool_name}", context)
                    else:
                        logger.info(f"[流式] 其他内容类型: {item_type}")

                now = time.time()
                if buf and now - last_flush > 5:
                    await _update_status(chat_id, f"⏳ Claude 回复中... ({len(buf)}字)", context)
                    last_flush = now

            elif msg_type == "result":
                logger.info(f"[流式] 收到 result, buf总计={len(buf)}字")
                await _delete_status()
                cost = data.get("total_cost_usd", 0)
                if cost:
                    state["session_cost"] += cost
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

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    ret = proc.poll()
    logger.info(f"[流式] 子进程退出码: {ret}")


async def _stream_send(text: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    _kill_stream_proc()

    logger.info(f"[流式] 启动子进程, prompt={text[:80]}, cwd={state['cwd']}")
    await _update_status(chat_id, "⏳ 启动 Claude...", context)

    env = os.environ.copy()
    env["CLAUDE_CODE_GIT_BASH_PATH"] = GIT_BASH_PATH

    cmd = [
        "claude.cmd", "-p",
        "--output-format", "stream-json",
        "--verbose",
    ]
    if os.environ.get("CLAUDE_SKIP_PERMISSIONS", "true").lower() in ("true", "1", "yes"):
        cmd.append("--dangerously-skip-permissions")
    cmd += ["--add-dir", state["cwd"], text]
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
