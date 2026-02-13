<div align="center">

# 🛏️ BedCode

**通过 Telegram 远程控制 Windows 上的 Claude Code。躺在床上写代码。**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram)](https://core.telegram.org/bots)

[中文](README.md) | [English](README_EN.md) | [日本語](README_JP.md)

</div>

---

## 🌟 功能特性

<table>
<tr>
<td width="50%">

### 💬 消息注入
直接向 Claude Code 终端发送文本。支持文本、图片、语音、文件，长消息自动保存。

### 📸 无干扰截屏
使用 Win32 PrintWindow API。不激活窗口，不打断 Claude 工作流。

### ⚡ 实时监控
通过窗口标题 spinner 字符自动检测 Claude 状态（思考中/空闲）。显示已用时间。

### 🎯 快速回复按钮
自动为 y/n、数字选项、❯ 选择器提示生成内联按钮。

### 📋 消息队列
Claude 思考时自动排队消息。完成后按顺序发送。

### ⌨️ 按键注入
使用 SendInput API 发送方向键、回车、数字等。

</td>
<td width="50%">

### 🪟 多窗口管理
扫描所有 Claude 窗口，支持自定义持久化标签和截图预览。

### 🖼️ 图片粘贴 (Alt+V)
通过剪贴板 + Alt+V 将 Telegram 图片直接粘贴到 Claude Code，如同桌面拖放。

### 🎤 语音消息
通过 OpenAI Whisper API 转录语音消息并注入文本到 Claude Code。

### 📄 文件上传
从 Telegram 直接发送文件（.py, .json, .txt 等）到工作目录。

### 🌊 流式模式
运行 `claude -p` 子进程，实时转发 JSON 流。

### 📜 命令历史
使用 `/history` 查看并重发最近 20 条消息。

### 🐚 Shell 执行
使用 `!command` 前缀执行本地 shell 命令。

### 🔔 Hook 通知
通过 `notify_hook.py` 自动推送 Claude 的响应。

### 🔄 热重载
使用 `/reload` 重载 `.env` 配置，无需重启。

</td>
</tr>
</table>

---

## 📷 截图展示

<!-- Add screenshots here -->

---

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.10 或更高版本
- 已安装 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Git Bash（Windows 上的 Claude Code 需要）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

从模板创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 填入你的配置：

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789,987654321
WORK_DIR=C:\Users\YourName\Projects
GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
SCREENSHOT_DELAY=1.5
SHELL_TIMEOUT=30
CLAUDE_TIMEOUT=300
```

### 4. 设置 Claude Code Hook（可选）

在 `~/.claude/settings.json` 中添加：

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

### 5. 运行 Bot

```bash
python bot.py
```

---

## 📖 命令列表

| 命令 | 说明 | 示例 |
|---------|-------------|---------|
| 🏠 `/start` | 显示欢迎消息和可用命令 | `/start` |
| 📸 `/screenshot` | 截取 Claude Code 窗口截图 | `/screenshot` |
| 📝 `/grab` | 抓取 Claude Code 窗口当前文本 | `/grab` |
| ⌨️ `/key` | 注入键盘输入（方向键、回车、数字） | `/key down` |
| 👁️ `/watch` | 开始监控 Claude 状态（自动截图） | `/watch` |
| 🛑 `/stop` | 停止监控 | `/stop` |
| ⏱️ `/delay` | 设置截图延迟（秒） | `/delay 2.0` |
| 🤖 `/auto` | 切换队列消息自动发送模式 | `/auto on` |
| 🪟 `/windows` | 列出所有 Claude Code 窗口 | `/windows` |
| ➕ `/new` | 以流式模式启动新的 Claude Code 会话 | `/new` |
| 📂 `/cd` | 更改工作目录 | `/cd C:\Projects` |
| 📜 `/history` | 查看并重发最近 20 条消息 | `/history` |
| 🔄 `/reload` | 热重载 `.env` 配置，无需重启 | `/reload` |

### 特殊前缀

- `!command` - 执行 shell 命令（例如 `!dir`、`!git status`）
- 发送图片 - 通过 Alt+V 剪贴板粘贴到 Claude Code
- 发送语音消息 - 通过 Whisper API 转录后注入文本
- 发送文件（.py, .json, .txt 等）- 保存到工作目录并注入路径

---

## 🏗️ 架构设计

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
│  │   消息处理   │  │   截图捕获   │  │   状态检测   │      │
│  │   Message    │  │  Screenshot  │  │    State     │      │
│  │   Handler    │  │   Capture    │  │  Detection   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   按键注入   │  │   队列管理   │  │   流式模式   │      │
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

## 🔍 工作原理

### 状态检测机制

BedCode 通过监控 Claude Code 的窗口标题来检测其当前状态：

```
窗口标题分析
│
├─ 包含盲文字符 (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) → Claude 正在思考
│  └─ 消息排队，等待完成
│
├─ 包含 ✳ 符号 → Claude 空闲
│  └─ 可以安全发送消息
│
└─ 标题改变 → 检测到状态转换
   └─ 处理队列中的消息
```

**流程图：**

```
用户通过 Telegram 发送消息
         │
         ▼
    Claude 是否空闲？
         │
    ┌────┴────┐
    │         │
   是        否
    │         │
    │         └──► 添加到队列
    │              │
    │              ▼
    │         监控状态
    │              │
    │              ▼
    │         Claude 空闲？
    │              │
    │             是
    │              │
    └──────────────┘
         │
         ▼
   注入消息
         │
         ▼
   截取屏幕
         │
         ▼
   发送到 Telegram
```

---

## 🔒 安全说明

> **⚠️ 警告**
>
> - 此 Bot 提供对 Claude Code 实例的**完全控制**
> - 仅将**可信用户 ID** 添加到 `ALLOWED_USER_IDS`
> - 保护好你的 `TELEGRAM_BOT_TOKEN`
> - 不要在公开仓库中暴露 Bot Token
> - 考虑在专用机器或虚拟机上运行 Bot
> - 执行前检查所有 shell 命令

---

## 📁 项目结构

```
Bedcode/
├── bot.py              # 入口：应用构建、信号处理
├── config.py           # 配置加载、日志、全局状态、常量
├── win32_api.py        # Win32 截屏、按键注入、剪贴板、窗口操作
├── claude_detect.py    # 状态检测、窗口扫描、终端文本读取
├── monitor.py          # 监控循环、交互提示检测、状态消息
├── stream_mode.py      # Git Bash 检测、子进程管理、流式读取
├── handlers.py         # 所有 Telegram 命令/回调/消息处理
├── utils.py            # 文本分割、结果发送、文件保存、路径持久化
├── notify_hook.py      # Claude Code hook 响应通知
├── requirements.txt    # Python 依赖
├── .env.example        # 配置模板
├── README.md           # 中文文档（默认）
├── README_EN.md        # 英文文档
└── README_JP.md        # 日文文档
```

---

## 🛠️ 配置参考

### 环境变量

| 变量 | 说明 | 默认值 | 必需 |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | 从 @BotFather 获取的 Telegram Bot Token | - | ✅ |
| `ALLOWED_USER_IDS` | 允许的 Telegram 用户 ID（逗号分隔） | - | ✅ |
| `WORK_DIR` | Claude Code 的默认工作目录 | 当前目录 | ❌ |
| `GIT_BASH_PATH` | Git Bash 可执行文件路径 | `C:\Program Files\Git\bin\bash.exe` | ❌ |
| `SCREENSHOT_DELAY` | 监控模式下截图间隔（秒） | `1.5` | ❌ |
| `SHELL_TIMEOUT` | Shell 命令超时（秒） | `30` | ❌ |
| `CLAUDE_TIMEOUT` | Claude 操作超时（秒） | `300` | ❌ |
| `OPENAI_API_KEY` | OpenAI API 密钥，用于语音消息转录（Whisper） | - | ❌ |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥，用于图片分析（Vision API 备选） | - | ❌ |

---

## 🤝 贡献

欢迎贡献！请随时提交 Pull Request。对于重大更改，请先开 issue 讨论你想要改变的内容。

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

---

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [Anthropic](https://www.anthropic.com/) 提供 Claude Code
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 提供优秀的 Telegram Bot 框架
- [pywinauto](https://github.com/pywinauto/pywinauto) 提供 Windows UI 自动化

---

## ⭐ Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=cass-2003/Bedcode&type=Date)](https://star-history.com/#cass-2003/Bedcode&Date)

---

<div align="center">

**用 ❤️ 为躺在床上写代码的懒惰开发者打造**

[报告 Bug](https://github.com/cass-2003/Bedcode/issues) · [请求功能](https://github.com/cass-2003/Bedcode/issues)

</div>
