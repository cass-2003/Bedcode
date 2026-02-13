<div align="center">

# 🛏️ BedCode

**Remote control Claude Code on Windows via Telegram. Code from your bed.**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram)](https://core.telegram.org/bots)

[English](README.md) | [中文](README_CN.md) | [日本語](README_JP.md)

</div>

---

## 🌟 Features

<table>
<tr>
<td width="50%">

### 💬 Message Injection
Send text directly to Claude Code terminal. Supports text, images, voice, files, and auto-saves long messages.

### 📸 Non-Intrusive Screenshot
Uses Win32 PrintWindow API. Doesn't activate window or interrupt Claude's workflow.

### ⚡ Real-Time Monitoring
Auto-detects Claude state (thinking/idle) via window title spinner characters. Shows elapsed time.

### 🎯 Quick Reply Buttons
Auto-generates inline buttons for y/n, numbered options, and ❯ selector prompts.

### 📋 Message Queue
Auto-queues messages while Claude is thinking. Sends sequentially after completion.

### ⌨️ Key Injection
Uses SendInput API for arrow keys, enter, numbers, and more.

</td>
<td width="50%">

### 🪟 Multi-Window Management
Scans all Claude windows with custom persistent labels and screenshot previews.

### 🖼️ Image Paste (Alt+V)
Pastes images from Telegram directly into Claude Code via clipboard + Alt+V, just like desktop drag-and-drop.

### 🎤 Voice Messages
Transcribes voice messages via OpenAI Whisper API and injects text to Claude Code.

### 📄 File Upload
Send files (.py, .json, .txt, etc.) from Telegram directly to the working directory.

### 🌊 Stream Mode
Runs `claude -p` subprocess with real-time JSON stream forwarding.

### 📜 Command History
View and resend last 20 messages with `/history`.

### 🐚 Shell Execution
Execute local shell commands with `!command` prefix.

### 🔔 Hook Notification
Auto-pushes Claude's responses via `notify_hook.py`.

### 🔄 Hot Reload
Reload `.env` config with `/reload` — no restart needed.

</td>
</tr>
</table>

---

## 📷 Screenshots

<!-- Add screenshots here -->

---

## 🚀 Quick Start

### 1. Prerequisites

- Windows 10/11
- Python 3.10 or higher
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Git Bash (for Claude Code on Windows)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789,987654321
WORK_DIR=C:\Users\YourName\Projects
GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
SCREENSHOT_DELAY=1.5
SHELL_TIMEOUT=30
CLAUDE_TIMEOUT=300
```

### 4. Setup Claude Code Hook (Optional)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Notification": {
      "command": "python C:\\path\\to\\notify_hook.py"
    },
    "Stop": {
      "command": "python C:\\path\\to\\notify_hook.py"
    }
  }
}
```

### 5. Run the Bot

```bash
python bot.py
```

---

## 📖 Commands

| Command | Description | Example |
|---------|-------------|---------|
| 🏠 `/start` | Show welcome message and available commands | `/start` |
| 📸 `/screenshot` | Take a screenshot of Claude Code window | `/screenshot` |
| 📝 `/grab` | Grab current text from Claude Code window | `/grab` |
| ⌨️ `/key` | Inject keyboard input (arrows, enter, numbers) | `/key down` |
| 👁️ `/watch` | Start monitoring Claude state (auto-screenshot) | `/watch` |
| 🛑 `/stop` | Stop monitoring | `/stop` |
| ⏱️ `/delay` | Set screenshot delay (seconds) | `/delay 2.0` |
| 🤖 `/auto` | Toggle auto-send mode for queued messages | `/auto on` |
| 🪟 `/windows` | List all Claude Code windows | `/windows` |
| ➕ `/new` | Start new Claude Code session in stream mode | `/new` |
| 📂 `/cd` | Change working directory | `/cd C:\Projects` |
| 📜 `/history` | View and resend last 20 messages | `/history` |
| 🔄 `/reload` | Hot-reload `.env` config without restart | `/reload` |

### Special Prefixes

- `!command` - Execute shell command (e.g., `!dir`, `!git status`)
- Send images - Pastes into Claude Code via Alt+V clipboard
- Send voice messages - Transcribed via Whisper API and injected as text
- Send files (.py, .json, .txt, etc.) - Saved to working directory and path injected

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot API                        │
│                   (python-telegram-bot)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        bot.py                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Message    │  │  Screenshot  │  │    State     │      │
│  │   Handler    │  │   Capture    │  │  Detection   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Key      │  │    Queue     │  │    Stream    │      │
│  │  Injection   │  │  Management  │  │     Mode     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Win32 API  │  │  pywinauto  │  │   subprocess│
│ PrintWindow │  │     UIA     │  │  (claude)   │
│  SendInput  │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
              ┌─────────────────────┐
              │   Claude Code CLI   │
              └─────────────────────┘
```

---

## 🔍 How It Works

### State Detection Mechanism

BedCode monitors Claude Code's window title to detect its current state:

```
Window Title Analysis
│
├─ Contains Braille chars (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) → Claude is THINKING
│  └─ Queue messages, wait for completion
│
├─ Contains ✳ symbol → Claude is IDLE
│  └─ Safe to send messages
│
└─ Title changed → State transition detected
   └─ Process queued messages if any
```

**Flow Diagram:**

```
User sends message via Telegram
         │
         ▼
    Is Claude idle?
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         └──► Add to queue
    │              │
    │              ▼
    │         Monitor state
    │              │
    │              ▼
    │         Claude idle?
    │              │
    │             YES
    │              │
    └──────────────┘
         │
         ▼
   Inject message
         │
         ▼
   Take screenshot
         │
         ▼
   Send to Telegram
```

---

## 🔒 Security

> **⚠️ WARNING**
>
> - This bot provides **full control** over your Claude Code instance
> - Only add **trusted user IDs** to `ALLOWED_USER_IDS`
> - Keep your `TELEGRAM_BOT_TOKEN` secret
> - Do not expose your bot token in public repositories
> - Consider running the bot on a dedicated machine or VM
> - Review all shell commands before execution

---

## 📁 Project Structure

```
Bedcode/
├── bot.py              # Entry point: app builder, signal handling
├── config.py           # Config loading, logging, global state, constants
├── win32_api.py        # Win32 screenshot, key injection, clipboard, window ops
├── claude_detect.py    # State detection, window scanning, terminal text reading
├── monitor.py          # Monitor loop, interactive prompt detection, status messages
├── stream_mode.py      # Git Bash detection, subprocess management, stream reader
├── handlers.py         # All Telegram command/callback/message handlers
├── utils.py            # Text splitting, result sending, file saving, path persistence
├── notify_hook.py      # Claude Code hook for response notifications
├── requirements.txt    # Python dependencies
├── .env.example        # Configuration template
├── README.md           # English documentation
├── README_CN.md        # Chinese documentation
└── README_JP.md        # Japanese documentation
```

---

## 🛠️ Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | - | ✅ |
| `ALLOWED_USER_IDS` | Comma-separated list of allowed Telegram user IDs | - | ✅ |
| `WORK_DIR` | Default working directory for Claude Code | Current dir | ❌ |
| `GIT_BASH_PATH` | Path to Git Bash executable | `C:\Program Files\Git\bin\bash.exe` | ❌ |
| `SCREENSHOT_DELAY` | Delay between screenshots in watch mode (seconds) | `1.5` | ❌ |
| `SHELL_TIMEOUT` | Timeout for shell commands (seconds) | `30` | ❌ |
| `CLAUDE_TIMEOUT` | Timeout for Claude operations (seconds) | `300` | ❌ |
| `OPENAI_API_KEY` | OpenAI API key for voice message transcription (Whisper) | - | ❌ |
| `ANTHROPIC_API_KEY` | Anthropic API key for image analysis (Vision API fallback) | - | ❌ |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude Code
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for the excellent Telegram Bot framework
- [pywinauto](https://github.com/pywinauto/pywinauto) for Windows UI automation

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=cass-2003/Bedcode&type=Date)](https://star-history.com/#cass-2003/Bedcode&Date)

---

<div align="center">

**Made with ❤️ for lazy developers who code from bed**

[Report Bug](https://github.com/cass-2003/Bedcode/issues) · [Request Feature](https://github.com/cass-2003/Bedcode/issues)

</div>
