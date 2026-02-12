# BedCode v5

通过 Telegram 远程操控 Windows 上的 Claude Code 终端。躺在床上也能写代码。

## 功能

- **消息注入** — 发消息直接注入 Claude Code 终端，支持文本、图片、长文件
- **无干扰截屏** — PrintWindow API 截屏，不激活窗口，不打断 Claude 思考
- **实时监控** — 自动检测 Claude 状态（思考中/空闲），完成后推送截图
- **交互提示检测** — 检测 y/n、选项菜单等提示，自动生成快速回复按钮
- **消息队列** — Claude 思考时消息自动排队，完成后依次发送，支持查看/清空
- **按键注入** — 通过 `/key` 发送方向键、回车等，远程选择选项
- **多窗口管理** — 扫描所有 Claude 窗口，自定义标签区分，截图预览
- **智能截图** — 内容未变时跳过发送，减少冗余通知
- **流式模式** — 通过 `claude -p` 子进程实时转发输出
- **Shell 执行** — `!命令` 前缀直接执行本地命令
- **Hook 通知** — Claude Code 完成时自动推送回复内容

## 环境要求

- Windows 10/11
- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装
- Git Bash（Claude Code 在 Windows 上需要）

## 安装

```bash
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode
pip install -r requirements.txt
```

## 配置

1. 复制配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env`，填入：
   - `TELEGRAM_BOT_TOKEN` — 从 [@BotFather](https://t.me/BotFather) 获取
   - `ALLOWED_USER_IDS` — 你的 Telegram User ID（从 [@userinfobot](https://t.me/userinfobot) 获取）
   - `WORK_DIR` — 默认工作目录
   - `GIT_BASH_PATH` — Git Bash 路径

## 使用

### 启动 Bot

```bash
python bot.py
```

### Telegram 命令

| 命令 | 说明 |
|------|------|
| `/start` | 查看状态 |
| `/screenshot` | 截屏 |
| `/grab` | 读取终端文本 |
| `/key <按键>` | 发送按键（如 `/key down down enter`） |
| `/watch` | 开始监控 |
| `/stop` | 停止监控 |
| `/delay <秒>` | 设置截图间隔 |
| `/auto` | 开关自动监控 |
| `/windows` | 扫描并选择窗口 |
| `/new [路径]` | 启动新 Claude 实例 |
| `/cd <路径>` | 切换工作目录 |

### 消息类型

- **普通文本** → 注入到 Claude Code 终端
- **`!命令`** → 执行本地 Shell 命令
- **图片** → 下载保存，注入图片路径给 Claude

### Hook 配置（可选）

在 Claude Code 设置中添加 hook，实现完成时自动推送回复：

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "python /path/to/notify_hook.py" }]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "python /path/to/notify_hook.py" }]
      }
    ]
  }
}
```

## 技术实现

- **PrintWindow API** — 无干扰窗口截屏
- **pywinauto UIA** — 终端文本读取
- **SendInput API** — 按键注入
- **python-telegram-bot** — 异步 Telegram Bot 框架

## License

MIT
