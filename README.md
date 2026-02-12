<p align="center">
  <h1 align="center">🛏️ BedCode v5</h1>
  <p align="center">
    <strong>通过 Telegram 远程操控 Windows 上的 Claude Code 终端</strong><br>
    躺在床上也能写代码
  </p>
  <p align="center">
    <a href="#功能特性">功能特性</a> •
    <a href="#快速开始">快速开始</a> •
    <a href="#使用指南">使用指南</a> •
    <a href="#架构设计">架构设计</a>
  </p>
</p>

---

## 为什么需要 BedCode？

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 是一个强大的 CLI 编程助手，但它运行在终端中，需要你坐在电脑前操作。BedCode 通过 Telegram Bot 桥接了这个限制——你可以在手机上随时随地向 Claude Code 发送指令、查看执行状态、处理交互提示，就像坐在电脑前一样。

**典型场景：**
- 🛏️ 躺在床上让 Claude 帮你写代码，手机上审查结果
- 🚶 出门在外，远程监控长时间运行的任务
- 📱 手机上快速回复 Claude 的 y/n 确认和选项选择
- 🖥️ 同时管理多个 Claude Code 窗口，互不干扰

## 功能特性

### 核心功能

| 功能 | 说明 |
|------|------|
| **消息注入** | 发送文本直接注入 Claude Code 终端，支持文本、图片、长文件自动保存 |
| **无干扰截屏** | 使用 Win32 PrintWindow API，不激活窗口、不打断 Claude 思考 |
| **实时状态监控** | 通过窗口标题 spinner 字符自动检测 Claude 状态（思考中/空闲） |
| **按键注入** | 通过 SendInput API 远程发送方向键、回车、数字等按键 |

### 智能功能

| 功能 | 说明 |
|------|------|
| **快速回复按钮** | 检测到 y/n、数字选项、选择器时自动生成 Telegram inline 按钮，一键回复 |
| **消息队列** | Claude 思考时消息自动排队，完成后依次发送，支持查看和清空队列 |
| **智能截图去重** | MD5 哈希比对，内容未变时跳过发送，减少冗余通知 |
| **交互提示检测** | 自动识别 `(y/n)`、`Select an option`、`❯` 选择器等交互模式 |

### 窗口管理

| 功能 | 说明 |
|------|------|
| **多窗口扫描** | 自动发现所有 Claude Code 窗口，显示状态和截图预览 |
| **自定义标签** | 给每个窗口设置标签（如项目名），持久化保存，重启不丢失 |
| **一键切换** | 通过 inline 按钮快速切换目标窗口 |
| **新实例启动** | 远程启动新的 Claude Code 实例，支持选择工作目录 |

### 其他

| 功能 | 说明 |
|------|------|
| **流式模式** | 通过 `claude -p --output-format stream-json` 子进程实时转发输出 |
| **Shell 执行** | `!命令` 前缀直接在本地执行 Shell 命令并返回结果 |
| **Hook 通知** | Claude Code 完成回复时自动推送内容到 Telegram |
| **图片支持** | 发送图片自动下载保存，将路径注入给 Claude 分析 |

## 快速开始

### 环境要求

- **操作系统**：Windows 10 / 11
- **Python**：3.10+
- **Claude Code**：已安装并可通过 `claude` 命令启动
- **Git Bash**：Claude Code 在 Windows 上需要（通常随 [Git for Windows](https://gitforwindows.org/) 安装）

### 安装

```bash
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode
pip install -r requirements.txt
```

**依赖说明：**

| 包 | 用途 |
|---|------|
| `python-telegram-bot[ext]` | Telegram Bot 异步框架 |
| `python-dotenv` | 环境变量管理 |
| `pywinauto` | Windows UI 自动化（UIA 文本读取） |
| `Pillow` | 图片处理（截图压缩） |

> `pywinauto` 和 `Pillow` 为系统级依赖，如未安装请手动 `pip install pywinauto Pillow`

### 配置

1. 复制配置模板：

```bash
cp .env.example .env
```

2. 编辑 `.env` 填入你的配置：

```ini
# 必填
TELEGRAM_BOT_TOKEN=your_bot_token_here    # 从 @BotFather 获取
ALLOWED_USER_IDS=123456789                 # 从 @userinfobot 获取，多个用逗号分隔

# 可选
WORK_DIR=C:\Users\YourName                # 默认工作目录
GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe  # Git Bash 路径
SCREENSHOT_DELAY=15                        # 截图间隔（秒）
SHELL_TIMEOUT=120                          # Shell 命令超时（秒）
CLAUDE_TIMEOUT=600                         # Claude 执行超时（秒）
```

**获取 Telegram 配置：**
1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)，发送 `/newbot` 创建 Bot，获取 Token
2. 搜索 [@userinfobot](https://t.me/userinfobot)，获取你的 User ID

### 启动

```bash
python bot.py
```

启动后在 Telegram 中向你的 Bot 发送任意消息即可开始使用。

## 使用指南

### Telegram 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/start` | 查看 Bot 状态、窗口列表、监控状态 | `/start` |
| `/screenshot` | 截取当前窗口截图 | `/screenshot` |
| `/grab` | 读取终端文本内容 | `/grab` |
| `/key <按键>` | 发送按键序列 | `/key down down enter` |
| `/watch` | 手动开始监控当前窗口 | `/watch` |
| `/stop` | 停止监控 | `/stop` |
| `/delay <秒>` | 设置监控截图间隔（3-300秒） | `/delay 10` |
| `/auto` | 开关自动监控（发消息后自动开始） | `/auto` |
| `/windows` | 扫描所有 Claude 窗口，显示截图预览 | `/windows` |
| `/new [路径]` | 启动新 Claude Code 实例 | `/new C:\Projects\myapp` |
| `/cd <路径>` | 切换 Shell 工作目录 | `/cd C:\Projects` |

### 消息类型

| 输入 | 行为 |
|------|------|
| 普通文本 | 注入到 Claude Code 终端 |
| `!命令` | 执行本地 Shell 命令（如 `!git status`） |
| 图片 | 下载保存，注入图片路径给 Claude |
| 图片 + 文字 | 下载图片，注入「文字 + 图片路径」 |

> 超过 200 字符或包含特殊字符的消息会自动保存为 `.md` 文件，注入文件路径。

### 按键映射

`/key` 命令支持以下按键名：

| 按键 | 别名 |
|------|------|
| `up` | `上`, `↑` |
| `down` | `下`, `↓` |
| `left` | `左` |
| `right` | `右` |
| `enter` | `回车` |
| `tab` | - |
| `esc` | `取消` |
| `space` | `空格` |
| `backspace` | `退格` |
| `1`-`9` | 直接输入数字 |

**示例：**
```
/key down enter          # 选择第二个选项
/key y enter             # 确认 y/n 提示
/key 2 enter             # 选择数字选项 2
/key up up enter         # 向上移动两次并确认
```

### 快速回复按钮

当监控检测到 Claude 弹出交互提示时，会自动生成对应的 inline 按钮：

- **y/n 提示** → `[✅ Yes]` `[❌ No]`
- **数字选项** → `[1]` `[2]` `[3]` ...
- **❯ 选择器** → `[↑]` `[↓]` `[✓ 确认]`

点击按钮即自动发送对应按键，无需手动输入 `/key`。

### 窗口管理

当你同时运行多个 Claude Code 实例时：

1. 发送 `/windows` 扫描所有窗口
2. 每个窗口会显示截图预览，帮助区分
3. 点击 ✏️ 按钮给窗口设置标签（如 `frontend`、`backend`）
4. 标签会持久化保存，重启 Bot 后仍然有效
5. 点击窗口按钮切换目标，后续消息将注入到选中的窗口

### 监控模式

监控模式会持续跟踪 Claude Code 的执行状态：

1. **自动监控**（默认开启）：发送消息后自动开始监控
2. **状态检测**：通过窗口标题的 spinner 字符判断 thinking/idle
3. **完成通知**：Claude 完成后发送最终截图
4. **消息队列**：思考中收到的消息自动排队，完成后依次发送
5. **智能截图**：定期截图但跳过内容未变的帧

### Hook 通知（可选）

配置 Claude Code Hook 后，Claude 完成回复时会自动将内容推送到 Telegram：

编辑 `~/.claude/settings.json`，添加：

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/path/to/Bedcode/notify_hook.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python C:/path/to/Bedcode/notify_hook.py"
          }
        ]
      }
    ]
  }
}
```

> 将路径替换为你的实际 BedCode 安装路径。Hook 脚本会读取同目录下的 `.env` 获取 Bot Token。

## 架构设计

### 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| Bot 框架 | `python-telegram-bot` (async) | Telegram Bot API 交互 |
| 窗口截屏 | Win32 `PrintWindow` API | 无干扰截屏，不激活窗口 |
| 文本读取 | `pywinauto` UIA backend | 从终端控件提取文本 |
| 按键注入 | Win32 `SendInput` API | 模拟键盘输入 |
| 窗口扫描 | `pywinauto` Desktop | 枚举所有 Claude Code 窗口 |
| 图片处理 | `Pillow` | 截图压缩和缩放 |

### 核心模块

```
bot.py
├── 截屏模块        PrintWindow API 无干扰截屏
├── 文本读取模块     UIA TextPattern 终端文本提取
├── 按键注入模块     SendInput API + pywinauto 文本注入
├── 窗口扫描模块     UIA Desktop 枚举 + 状态检测
├── 监控循环        异步状态轮询 + 交互提示检测 + 队列处理
├── 流式模式        claude -p 子进程 + JSON stream 解析
├── 命令处理        11 个 Telegram 命令 + inline 按钮回调
└── 消息路由        文本/图片/Shell/队列 分发

notify_hook.py
└── Claude Code Hook 回调 → 读取 transcript → 推送到 Telegram
```

### 状态检测原理

Claude Code 在 Windows Terminal 中运行时，窗口标题会随状态变化：

| 标题前缀 | 状态 | 含义 |
|----------|------|------|
| `⠋⠙⠸⠴...`（Braille spinner） | `thinking` | Claude 正在思考/执行 |
| `✳` | `idle` | Claude 等待输入 |

BedCode 通过 1.5 秒轮询窗口标题来检测状态变化，无需注入任何代码到 Claude Code 进程。

## 安全说明

- **用户鉴权**：通过 `ALLOWED_USER_IDS` 白名单限制，未授权用户无法使用 Bot
- **敏感信息**：Bot Token 和 User ID 存储在 `.env` 中，已通过 `.gitignore` 排除
- **权限范围**：Bot 具有窗口截屏、按键注入、Shell 执行能力，请确保只有你自己能访问

> ⚠️ 请勿将 `.env` 文件提交到公开仓库。

## 项目结构

```
Bedcode/
├── bot.py              # 主程序（Bot 逻辑、窗口操作、监控循环）
├── notify_hook.py      # Claude Code Hook 通知脚本
├── requirements.txt    # Python 依赖
├── .env.example        # 配置模板
├── .gitignore          # Git 排除规则
└── test_stream*.py     # 流式模式测试脚本
```

## License

MIT
