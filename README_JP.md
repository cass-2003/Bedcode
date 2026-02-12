<div align="center">

# 🛏️ BedCode

**Telegram経由でWindows上のClaude Codeをリモート制御。ベッドからコーディング。**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram)](https://core.telegram.org/bots)

[English](README.md) | [中文](README_CN.md) | [日本語](README_JP.md)

</div>

---

## 🌟 機能

<table>
<tr>
<td width="50%">

### 💬 メッセージ注入
Claude Codeターミナルに直接テキストを送信。テキスト、画像をサポートし、長いファイルは自動保存。

### 📸 非侵入型スクリーンショット
Win32 PrintWindow APIを使用。ウィンドウをアクティブ化せず、Claudeのワークフローを中断しません。

### ⚡ リアルタイム監視
ウィンドウタイトルのスピナー文字でClaude状態（思考中/アイドル）を自動検出。

### 🎯 クイック返信ボタン
y/n、番号付きオプション、❯セレクタープロンプト用のインラインボタンを自動生成。

### 📋 メッセージキュー
Claudeが思考中の間、メッセージを自動キューイング。完了後に順次送信。

### ⌨️ キー注入
SendInput APIを使用して矢印キー、Enter、数字などを送信。

</td>
<td width="50%">

### 🪟 マルチウィンドウ管理
カスタム永続ラベルとスクリーンショットプレビュー付きで全Claudeウィンドウをスキャン。

### 🔄 スマートスクリーンショット重複排除
MD5ハッシュ比較で変更のないフレームをスキップし、帯域幅を節約。

### 🌊 ストリームモード
`claude -p`サブプロセスをリアルタイムJSON ストリーム転送で実行。

### 🐚 シェル実行
`!command`プレフィックスでローカルシェルコマンドを実行。

### 🔔 フック通知
`notify_hook.py`経由でClaudeの応答を自動プッシュ。

### 📂 動的パスメモリ
最近使用したディレクトリを記憶し、素早くアクセス。

</td>
</tr>
</table>

---

## 📷 スクリーンショット

<!-- Add screenshots here -->

---

## 🚀 クイックスタート

### 1. 前提条件

- Windows 10/11
- Python 3.10以上
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)がインストール済み
- Git Bash（Windows上のClaude Codeに必要）

### 2. インストール

```bash
# リポジトリをクローン
git clone https://github.com/cass-2003/Bedcode.git
cd Bedcode

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 設定

テンプレートから`.env`ファイルを作成：

```bash
cp .env.example .env
```

`.env`を編集して設定を入力：

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=123456789,987654321
WORK_DIR=C:\Users\YourName\Projects
GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
SCREENSHOT_DELAY=1.5
SHELL_TIMEOUT=30
CLAUDE_TIMEOUT=300
```

### 4. Claude Code Hookの設定（オプション）

`~/.claude/settings.json`に追加：

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

### 5. Botを実行

```bash
python bot.py
```

---

## 📖 コマンド

| コマンド | 説明 | 例 |
|---------|-------------|---------|
| 🏠 `/start` | ウェルカムメッセージと利用可能なコマンドを表示 | `/start` |
| 📸 `/screenshot` | Claude Codeウィンドウのスクリーンショットを撮影 | `/screenshot` |
| 📝 `/grab` | Claude Codeウィンドウから現在のテキストを取得 | `/grab` |
| ⌨️ `/key` | キーボード入力を注入（矢印、Enter、数字） | `/key down` |
| 👁️ `/watch` | Claude状態の監視を開始（自動スクリーンショット） | `/watch` |
| 🛑 `/stop` | 監視を停止 | `/stop` |
| ⏱️ `/delay` | スクリーンショット遅延を設定（秒） | `/delay 2.0` |
| 🤖 `/auto` | キューメッセージの自動送信モードを切り替え | `/auto on` |
| 🪟 `/windows` | 全Claude Codeウィンドウをリスト表示 | `/windows` |
| ➕ `/new` | ストリームモードで新しいClaude Codeセッションを開始 | `/new` |
| 📂 `/cd` | 作業ディレクトリを変更 | `/cd C:\Projects` |

### 特殊プレフィックス

- `!command` - シェルコマンドを実行（例：`!dir`、`!git status`）
- 画像を直接送信 - BotがダウンロードしてパスをClaudeに注入

---

## 🏗️ アーキテクチャ

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

## 🔍 動作原理

### 状態検出メカニズム

BedCodeはClaude Codeのウィンドウタイトルを監視して現在の状態を検出します：

```
ウィンドウタイトル分析
│
├─ 点字文字を含む (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) → Claudeは思考中
│  └─ メッセージをキューイング、完了を待機
│
├─ ✳ シンボルを含む → Claudeはアイドル
│  └─ メッセージ送信が安全
│
└─ タイトルが変更 → 状態遷移を検出
   └─ キューメッセージがあれば処理
```

**フロー図：**

```
ユーザーがTelegram経由でメッセージを送信
         │
         ▼
    Claudeはアイドル？
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         └──► キューに追加
    │              │
    │              ▼
    │         状態を監視
    │              │
    │              ▼
    │         Claudeはアイドル？
    │              │
    │             YES
    │              │
    └──────────────┘
         │
         ▼
   メッセージを注入
         │
         ▼
   スクリーンショットを撮影
         │
         ▼
   Telegramに送信
```

---

## 🔒 セキュリティ

> **⚠️ 警告**
>
> - このBotはClaude Codeインスタンスへの**完全な制御**を提供します
> - `ALLOWED_USER_IDS`には**信頼できるユーザーID**のみを追加してください
> - `TELEGRAM_BOT_TOKEN`を秘密に保ってください
> - 公開リポジトリでBotトークンを公開しないでください
> - 専用マシンまたはVMでBotを実行することを検討してください
> - 実行前にすべてのシェルコマンドを確認してください

---

## 📁 プロジェクト構造

```
Bedcode/
├── bot.py              # メインBotロジックとコマンドハンドラー
├── notify_hook.py      # 応答通知用Claude Code hook
├── requirements.txt    # Python依存関係
├── .env.example        # 設定テンプレート
├── .gitignore          # Git無視ルール
├── test_stream*.py     # ストリームモードテストスクリプト
├── README.md           # 英語ドキュメント
├── README_CN.md        # 中国語ドキュメント
└── README_JP.md        # 日本語ドキュメント
```

---

## 🛠️ 設定リファレンス

### 環境変数

| 変数 | 説明 | デフォルト | 必須 |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | @BotFatherから取得したTelegram Botトークン | - | ✅ |
| `ALLOWED_USER_IDS` | 許可されたTelegramユーザーIDのカンマ区切りリスト | - | ✅ |
| `WORK_DIR` | Claude Codeのデフォルト作業ディレクトリ | 現在のディレクトリ | ❌ |
| `GIT_BASH_PATH` | Git Bash実行ファイルへのパス | `C:\Program Files\Git\bin\bash.exe` | ❌ |
| `SCREENSHOT_DELAY` | 監視モードでのスクリーンショット間隔（秒） | `1.5` | ❌ |
| `SHELL_TIMEOUT` | シェルコマンドのタイムアウト（秒） | `30` | ❌ |
| `CLAUDE_TIMEOUT` | Claude操作のタイムアウト（秒） | `300` | ❌ |

---

## 🤝 コントリビューション

コントリビューションを歓迎します！お気軽にPull Requestを送信してください。大きな変更の場合は、まずissueを開いて変更内容について議論してください。

1. リポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. Pull Requestを開く

---

## 📝 ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

---

## 🙏 謝辞

- [Anthropic](https://www.anthropic.com/) - Claude Codeの提供
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 優れたTelegram Botフレームワーク
- [pywinauto](https://github.com/pywinauto/pywinauto) - Windows UI自動化

---

## ⭐ Star履歴

[![Star History Chart](https://api.star-history.com/svg?repos=cass-2003/Bedcode&type=Date)](https://star-history.com/#cass-2003/Bedcode&Date)

---

<div align="center">

**ベッドからコーディングする怠惰な開発者のために ❤️ で作成**

[バグ報告](https://github.com/cass-2003/Bedcode/issues) · [機能リクエスト](https://github.com/cass-2003/Bedcode/issues)

</div>
