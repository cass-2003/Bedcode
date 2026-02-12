#!/usr/bin/env python3
"""BedCode Notification Hook — Claude Code 完成时自动发送结果到 Telegram

支持两种 hook 事件:
- Notification: Claude Code 发通知时触发，直接拿通知内容
- Stop: Claude 完成回复时触发，从 transcript 读取最后的 assistant 回复
"""
import sys
import json
import os
import urllib.request

from dotenv import load_dotenv

# 加载 .env（与 bot.py 同目录）
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("ALLOWED_USER_IDS", "").split(",")[0].strip()

# 代理绕过（与 bot.py 一致）
for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(key, None)


def send_telegram(text: str) -> bool:
    """通过 Telegram Bot API 发送消息。"""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    # 截断过长消息，分片发送
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text)
            break
        idx = text.rfind("\n", 0, 4000)
        if idx == -1:
            idx = 4000
        chunks.append(text[:idx])
        text = text[idx:].lstrip("\n")

    for i, chunk in enumerate(chunks):
        prefix = f"[{i+1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
        payload = json.dumps({
            "chat_id": int(CHAT_ID),
            "text": f"{prefix}{chunk}",
        }).encode("utf-8")
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            return False
    return True


def read_last_response(transcript_path: str) -> str:
    """从 transcript 文件读取最后一条 assistant 回复。"""
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""

    # transcript 可能是列表或含 messages 键的字典
    messages = data if isinstance(data, list) else data.get("messages", [])

    # 从后往前找最后一条 assistant 消息
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                # content 可能是 [{type: "text", text: "..."}, ...] 格式
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                return "\n".join(parts)
            return str(content)
    return ""


def handle_notification(input_data: dict) -> None:
    """处理 Notification 事件。"""
    title = input_data.get("title", "")
    body = input_data.get("body", "")
    message = input_data.get("message", "")

    text = title or message or body
    if not text:
        return

    msg = f"🔔 Claude Code\n\n{text}"
    if body and body != text:
        msg += f"\n{body}"

    send_telegram(msg.strip())


def handle_stop(input_data: dict) -> None:
    """处理 Stop 事件 — 从 transcript 读取完整回复。"""
    transcript_path = input_data.get("transcript_path", "")
    stop_reason = input_data.get("stop_reason", "")

    response = read_last_response(transcript_path)
    if not response or len(response.strip()) < 5:
        return

    # 构建消息
    header = "📝 Claude 回复"
    if stop_reason:
        header += f" ({stop_reason})"

    send_telegram(f"{header}\n\n{response}")


def main():
    # Claude Code hook 通过 stdin 传入 JSON
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        input_data = {}

    hook_event = input_data.get("hook_event_name", "")

    if hook_event == "Notification":
        handle_notification(input_data)
    elif hook_event == "Stop":
        handle_stop(input_data)
    else:
        # 兼容旧格式 / 未知事件
        handle_notification(input_data)

    # hook 必须输出 JSON 响应
    json.dump({"continue": True}, sys.stdout)


if __name__ == "__main__":
    main()
