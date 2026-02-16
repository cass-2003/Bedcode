<div align="center">

# 🛏️ BedCode

**通过 Telegram + Web 远程控制 Windows 上的 Claude Code。躺在床上写代码。**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram)](https://core.telegram.org/bots)
[![Web UI](https://img.shields.io/badge/Web-PWA-green.svg)](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
[![Mobile App](https://img.shields.io/badge/Mobile-Expo-blueviolet.svg?logo=expo)](https://expo.dev/)

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
通过窗口标题 spinner 字符自动检测 Claude 状态（思考中/空闲）。实时更新思考计时。

### 👁️ 被动监控
在电脑上直接操作 Claude Code 时，结果自动转发到 Telegram/Web。Bot 启动后常驻运行。

### 🎯 快速回复按钮
自动为 y/n、数字选项、❯ 选择器提示生成内联按钮。

### 📋 消息队列
Claude 思考时自动排队消息。完成后按顺序发送。

### ⌨️ 按键注入
使用 SendInput API 发送方向键、回车、数字等。

</td>
<td width="50%">

### 🌐 Web/PWA 控制台
免翻墙的 Web 界面，对话气泡风格，支持深色/浅色主题，可安装为 PWA。

### 🪟 多窗口管理
扫描所有 Claude 窗口，支持自定义持久化标签和截图预览。

### 🖼️ 图片粘贴 (Alt+V)
通过剪贴板 + Alt+V 将图片直接粘贴到 Claude Code。Telegram 和 Web 端均支持。

### 🎤 语音消息
通过 OpenAI Whisper API 转录语音消息并注入文本到 Claude Code。

### 📄 文件上传
从 Telegram 直接发送文件（.py, .json, .txt 等）到工作目录。

### 🌊 流式模式
运行 `claude -p` 子进程，实时转发 JSON 流。

### 💰 会话成本追踪
实时追踪 API 调用成本，支持 `/cost` 查看和 `/export` 导出。

### 🔄 热重载 & 看门狗
使用 `/reload` 重载配置；`watchdog.py` 自动重启崩溃的 Bot。

</td>
</tr>
</table>

---

## 📱 Mobile App (v2.0)

原生移动客户端，基于 React Native + Expo，提供完整的远程控制体验。

### 新增功能

| 功能 | 说明 |
|------|------|
| 🪟 多窗口管理 | 切换/监控多个 Claude Code 窗口，独立消息流 |
| 👁️ 自动截屏监控 | Claude 思考时自动截屏推送到聊天 |
| 🎛️ 底部快捷操作栏 | 截屏/窗口/监控/停止/状态/剪贴板一键操作 |
| ⌨️ /命令系统 | 输入框直接输入 `/screenshot`、`/watch`、`/stop` 等命令 |
| 📝 消息模板 | 保存常用指令，快速发送 |
| 📦 批量发送 | 一次发送多条消息 |
| 🔍 历史搜索 | 搜索聊天历史记录 |
| ⏰ 定时任务 | 延时发送消息 |
| 🎛️ 自定义面板 | 自定义快捷按钮 |
| 🔗 命令别名 | 自定义命令快捷方式 |

### UI 特性

- TG 风格聊天气泡（发送/接收/系统/截图）
- 毛玻璃半透明顶栏，显示当前窗口名称和 Claude 状态
- 图片自适应宽高比（竖图/横图智能缩放）
- 深色/浅色主题自动切换
- 图片全屏查看器

### 运行 Mobile App

```bash
cd mobile
npm install
npx expo start --tunnel
```

扫描终端中的二维码即可在手机上打开。

---

## 🏗️ 架构设计

BedCode 采用双通道架构：Telegram Bot + Web API 并行运行，共享同一个核心。

```
┌──────────────┐     ┌──────────────┐
│  Telegram    │     │   Web/PWA    │
│  (手机/PC)   │     │  (浏览器)    │
└──────┬───────┘     └──────┬───────┘
       │                     │
       ▼                     ▼
┌──────────────┐     ┌──────────────────────┐
│ python-      │     │ FastAPI + uvicorn     │
│ telegram-bot │     │ REST API + WebSocket  │
└──────┬───────┘     └──────┬───────────────┘
       │                     │
       └──────────┬──────────┘
                  │
                  ▼
       ┌─────────────────────┐
       │     Core Modules     │
       │  ┌───────┐ ┌──────┐ │
       │  │monitor│ │config│ │
       │  │handler│ │utils │ │
       │  └───────┘ └──────┘ │
       └──────────┬──────────┘
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
  ┌─────────┐ ┌────────┐ ┌──────────┐
  │Win32 API│ │pywinauto│ │subprocess│
  │PrintWin │ │  UIA   │ │ (claude) │
  └─────────┘ └────────┘ └──────────┘
                  │
                  ▼
       ┌─────────────────────┐
       │   Claude Code CLI   │
       └─────────────────────┘
```

### EventBus 实时推送

```
monitor.py 事件 ──► EventBus ──► WebSocket ──► Web 浏览器
                       │
                       └──► (可扩展更多订阅者)
```

---

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装
- Git Bash（Windows 上的 Claude Code 需要）

### 2. 安装

```bash
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode
pip install -r requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
```

编辑 `.env`：

```env
# 必需
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789

# 可选
WORK_DIR=C:\Users\YourName\Projects
GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
CLAUDE_TIMEOUT=600
SHELL_TIMEOUT=120

# Web API（留空则自动生成）
BEDCODE_API_TOKEN=your_token_here
```

### 4. 运行

```bash
python bot.py
```

启动后同时运行：
- Telegram Bot（需翻墙）
- Web API `http://0.0.0.0:8080`（局域网直接访问）

### 5. Web 访问

浏览器打开 `http://<你的IP>:8080`，输入 `BEDCODE_API_TOKEN` 即可使用。

支持安装为 PWA（手机浏览器 → 添加到主屏幕）。

---

## 📖 Telegram 命令

| 命令 | 说明 |
|------|------|
| `/start` | 欢迎消息 |
| `/screenshot` | 截取 Claude 窗口 |
| `/grab` | 抓取终端文本 |
| `/key` | 注入键盘输入 |
| `/watch` | 开始监控 |
| `/stop` | 停止监控 |
| `/windows` | 列出所有 Claude 窗口 |
| `/cd` | 更改工作目录 |
| `/history` | 查看/重发历史消息 |
| `/cost` | 查看会话成本 |
| `/export` | 导出对话记录 |
| `/undo` | 撤销上次操作 |
| `/new` | 启动流式模式会话 |
| `/reload` | 热重载配置 |
| `/delay` | 设置截图间隔 |
| `/auto` | 切换自动发送 |
| `/autoyes` | 自动确认安全操作 |
| `/quiet` | 设置免打扰时段 |
| `/tpl` | 消息模板管理 |
| `/schedule` | 定时任务 |
| `/proj` | 项目快速切换 |
| `/batch` | 批量发送消息 |
| `/pin` | 窗口标签管理 |
| `/health` | 系统健康检查 |
| `/watchdog` | 看门狗状态 |

**特殊前缀：**
- `!command` — 执行 shell 命令
- 发送图片 — Alt+V 粘贴到 Claude
- 发送语音 — Whisper 转录后注入
- 发送文件 — 保存到工作目录

---

## 🌐 Web API

所有 API 端点需要 `Authorization: Bearer <token>` 头。

### REST 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/status` | Claude 状态（state/title/handle） |
| `GET` | `/api/screenshot` | 截图（返回 PNG） |
| `POST` | `/api/send` | 发送文本消息 |
| `POST` | `/api/image` | 上传图片（Alt+V 粘贴） |
| `POST` | `/api/keys` | 发送按键序列 |
| `POST` | `/api/break` | 发送 Ctrl+C 中断 |
| `POST` | `/api/undo` | 发送 Ctrl+Z 撤销 |
| `GET` | `/api/grab` | 抓取终端文本 |
| `GET` | `/api/windows` | 列出所有 Claude 窗口 |
| `POST` | `/api/target` | 切换目标窗口 |
| `GET` | `/api/queue` | 查看消息队列 |
| `DELETE` | `/api/queue` | 清空队列 |
| `GET` | `/api/history` | 命令历史 |
| `GET` | `/api/cost` | 会话成本 |
| `PATCH` | `/api/config` | 修改运行时配置 |
| `POST` | `/api/shell` | 执行 shell 命令 |
| `POST` | `/api/batch` | 批量发送消息 |
| `GET` | `/api/health` | 健康检查 |

### WebSocket

连接 `ws://<host>:8080/ws`，首条消息发送 `{"token": "..."}` 认证。

事件类型：`screenshot` | `status` | `text` | `result` | `completion`

---

## 📁 项目结构

```
BedCode/
├── bot.py              # 入口：TG 非阻塞启动 + uvicorn 主循环
├── config.py           # 配置加载、日志、全局状态
├── handlers.py         # Telegram 命令/回调/消息处理
├── monitor.py          # 监控循环、状态检测、EventBus 事件发射
├── win32_api.py        # Win32 截屏、按键注入、剪贴板、窗口操作
├── claude_detect.py    # Claude 状态检测、窗口扫描、终端文本读取
├── stream_mode.py      # Git Bash 子进程管理、流式读取
├── utils.py            # 文本分割、结果发送、文件/路径持久化
├── notify_hook.py      # Claude Code hook 完成通知
├── health.py           # 独立健康检查端点
├── watchdog.py         # 自动重启看门狗
├── core/
│   └── events.py       # EventBus（asyncio.Queue 广播）
├── api/
│   ├── app.py          # FastAPI 应用、CORS、token 认证
│   ├── routes.py       # REST 端点
│   └── ws.py           # WebSocket 端点
├── web/
│   ├── index.html      # Web UI（对话气泡风格 PWA）
│   ├── manifest.json   # PWA manifest
│   ├── sw.js           # Service Worker
│   └── icon.svg        # 应用图标
├── .env.example        # 配置模板
├── requirements.txt    # Python 依赖
└── mobile/             # React Native 移动客户端 (Expo)
    ├── app/            # Expo Router 页面
    │   ├── (tabs)/     # Tab 导航（聊天/窗口/设置）
    │   └── _layout.tsx # 根布局 + 自动监控挂载
    ├── components/     # UI 组件
    │   ├── ChatBubble.tsx    # TG 风格聊天气泡
    │   ├── ChatInput.tsx     # 输入框 + /命令补全
    │   ├── StatusHeader.tsx  # 毛玻璃顶栏
    │   ├── ActionBar.tsx     # 底部快捷操作栏
    │   ├── ImageViewer.tsx   # 图片全屏查看
    │   ├── CommandBar.tsx    # 命令面板
    │   ├── TemplatePanel.tsx # 模板管理
    │   ├── BatchPanel.tsx    # 批量发送
    │   └── HistoryPanel.tsx  # 历史搜索
    ├── stores/chatStore.ts   # Zustand 状态管理
    ├── hooks/
    │   ├── useApi.ts         # API 封装
    │   ├── useAutoMonitor.ts # 自动截屏监控
    │   └── useScheduler.ts   # 定时任务
    ├── constants/theme.ts    # 主题色彩
    ├── app.json              # Expo 配置
    └── package.json          # 依赖
```

---

## 🛠️ 配置参考

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | - | ✅ |
| `ALLOWED_USER_IDS` | 允许的用户 ID（逗号分隔） | - | ✅ |
| `WORK_DIR` | 默认工作目录 | 当前目录 | ❌ |
| `GIT_BASH_PATH` | Git Bash 路径 | 自动检测 | ❌ |
| `CLAUDE_TIMEOUT` | Claude 操作超时（秒） | `600` | ❌ |
| `SHELL_TIMEOUT` | Shell 命令超时（秒） | `120` | ❌ |
| `BEDCODE_API_TOKEN` | Web API Token | 自动生成 | ❌ |
| `OPENAI_API_KEY` | Whisper 语音转录 | - | ❌ |
| `ANTHROPIC_API_KEY` | Vision 图片分析 | - | ❌ |

---

## 🔒 安全说明

> **⚠️ 警告**
>
> - 此工具提供对 Claude Code 实例的**完全控制**
> - 仅将**可信用户 ID** 添加到 `ALLOWED_USER_IDS`
> - 保护好 `TELEGRAM_BOT_TOKEN` 和 `BEDCODE_API_TOKEN`
> - Web API 默认监听 `0.0.0.0:8080`，建议配合 Cloudflare Tunnel / Tailscale 使用
> - 不要在公开仓库中暴露任何 Token

---

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [Anthropic](https://www.anthropic.com/) — Claude Code
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot 框架
- [pywinauto](https://github.com/pywinauto/pywinauto) — Windows UI 自动化
- [FastAPI](https://fastapi.tiangolo.com/) — Web API 框架

---

<div align="center">

**用 ❤️ 为躺在床上写代码的懒惰开发者打造**

</div>
