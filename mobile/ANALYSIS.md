# BedCode Mobile App — 技术分析文档

## 1. 项目概述

BedCode Mobile 是 BedCode 的移动客户端，采用 Telegram 风格 UI，通过 REST + WebSocket 连接 BedCode 服务端，实现远程控制 Claude Code。

## 2. 技术选型

| 维度 | 选择 | 理由 |
|------|------|------|
| 框架 | React Native (Expo SDK 52) | JS/TS 全栈友好，Expo 工具链完整 |
| 路由 | Expo Router v4 | 文件系统路由，类 Next.js |
| 状态管理 | Zustand | 轻量，无 boilerplate |
| 安全存储 | expo-secure-store | iOS Keychain / Android Keystore |
| 图片选择 | expo-image-picker | 相册/相机选图 |
| 动画 | react-native-reanimated | 消息滑入、长按菜单 |
| 手势 | react-native-gesture-handler | 左滑回复、pinch zoom |

## 3. 设计风格 — Telegram 克隆

### 3.1 视觉规范

**深色模式**
- 背景: `#212121`
- 发送气泡: `#2B5278`
- 接收气泡: `#182533`
- 系统消息: `#1A1A1A` + 白色文字 60% 透明
- 输入栏背景: `#1C1C1C`
- 强调色: `#64B5F6`

**浅色模式**
- 背景: `#FFFFFF`
- 发送气泡: `#EFFDDE`
- 接收气泡: `#FFFFFF` + 阴影
- 输入栏背景: `#F0F0F0`
- 强调色: `#2196F3`

**气泡设计**
- 圆角: 16px，尾巴侧 2px
- 最大宽度: 屏幕 75%
- padding: 8px 12px
- 时间戳: 气泡右下角，11px，60% 透明度
- 连续同方向消息合并尾巴

### 3.2 交互规范

- 消息列表: FlatList inverted，底部输入
- 输入栏: 左侧 📎 附件，右侧 发送/语音 切换
- 长按消息: 浮动菜单（复制/重发）
- thinking 状态: 三点跳动动画 + 计时器
- 截图: 缩略图气泡，点击全屏 pinch zoom
- 快捷回复: y/n prompt 自动生成 inline 按钮

## 4. 通信协议

### 4.1 现有 API（Phase 1 直连 PC）

**认证**: `Authorization: Bearer <token>`

**REST 端点**:
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/status | Claude 状态 |
| GET | /api/screenshot | 截图 PNG |
| POST | /api/send | 发送消息 `{text}` |
| POST | /api/image | 上传图片 multipart |
| POST | /api/keys | 按键 `{keys:[]}` |
| POST | /api/break | Ctrl+C |
| POST | /api/undo | Ctrl+Z |
| GET | /api/grab | 终端文本 |
| GET | /api/windows | 窗口列表 |
| POST | /api/target | 切换窗口 `{handle}` |
| GET | /api/queue | 消息队列 |
| DELETE | /api/queue | 清空队列 |
| GET | /api/history | 命令历史 |
| GET | /api/cost | 费用 |
| PATCH | /api/config | 修改配置 |
| POST | /api/shell | Shell 命令 `{cmd}` |
| POST | /api/batch | 批量消息 `{messages:[]}` |

**WebSocket**: `ws://<host>/ws`
- 认证: 首条消息 `{"token": "..."}`
- 事件: screenshot / status / text / result / completion / pong
- 心跳: `{"action": "ping"}` → `{"type": "pong"}`

### 4.2 未来服务器中继（Phase 3）

```
App ←HTTPS/WSS→ 云服务器 ←WS隧道→ Windows PC
```
- JWT 认证（access + refresh token）
- 离线消息队列
- 消息持久化
- 推送通知（APNs/FCM）
- 多设备同步

## 5. 消息状态机

```
发送 → ✓ 已发送(服务端收到) → ✓✓ 已注入(Claude窗口)
                             → 🕐 排队中(Claude thinking)
                             → ❌ 失败
```

## 6. 文件管理（Phase 2）

需新增 API:
```
GET  /api/files?path=         → 目录列表
GET  /api/files/content?path= → 文件内容
GET  /api/files/download?path=→ 下载
POST /api/files/upload        → 上传
```

App 端: 文件浏览器 + 代码预览（语法高亮）+ 上传/下载

## 7. 分阶段路线

### Phase 1 — 核心聊天（当前）
- TG 风格聊天 UI（气泡/输入栏/状态栏）
- 直连 PC REST + WebSocket
- 截图查看
- 快捷操作（截屏/中断/撤销/Grab）
- 多窗口切换
- 深色/浅色主题
- 本地消息存储（AsyncStorage）

### Phase 2 — 文件管理
- 文件浏览器
- 代码预览
- 上传/下载

### Phase 3 — 云服务器
- 中继服务器
- JWT 认证
- 消息持久化
- 多设备同步

### Phase 4 — 推送 + 高级
- APNs/FCM 推送
- 费用趋势图表
- 离线消息队列
- 设备管理

## 8. 项目结构

```
mobile/
├── app/                     # Expo Router 页面
│   ├── _layout.tsx          # 根布局
│   ├── login.tsx            # 登录页（输入 host + token）
│   ├── (tabs)/
│   │   ├── _layout.tsx      # Tab 导航
│   │   ├── index.tsx        # 对话列表（多窗口）
│   │   ├── chat.tsx         # 聊天页
│   │   └── settings.tsx     # 设置页
│   └── screenshot.tsx       # 截图全屏查看
├── components/
│   ├── ChatBubble.tsx       # 消息气泡（含尾巴）
│   ├── ChatInput.tsx        # 输入栏
│   ├── StatusHeader.tsx     # 顶部状态栏
│   ├── QuickActions.tsx     # 快捷操作面板
│   ├── ThinkingIndicator.tsx# 思考中动画
│   ├── ScreenshotMsg.tsx    # 截图消息气泡
│   └── WindowList.tsx       # 窗口列表
├── hooks/
│   ├── useWebSocket.ts      # WS 连接管理
│   └── useApi.ts            # REST 请求封装
├── stores/
│   └── chatStore.ts         # Zustand 状态
├── constants/
│   └── theme.ts             # 主题色值
├── app.json                 # Expo 配置
├── package.json
└── tsconfig.json
```

## 9. 开源参考

| 项目 | 用途 |
|------|------|
| [icenfame/telegram](https://github.com/icenfame/telegram) | Expo + RN TG 克隆，参考结构 |
| [DrKLO/Telegram](https://github.com/DrKLO/Telegram) | 官方 Android，参考设计参数 |
| [GFean/react-native-chat-bubble](https://github.com/GFean/react-native-chat-bubble) | 气泡组件参考 |
| [getstream.io TG clone 教程](https://getstream.io/blog/telegram-clone-react-native/) | Expo TG 克隆教程 |

## 10. 调试方式

| 方式 | 命令 | 场景 |
|------|------|------|
| 浏览器 | `npx expo start --web` | 快速调 UI |
| Expo Go + tunnel | `npx expo start --tunnel` | 代理环境手机调试 |
| Expo Go + 局域网 | `npx expo start` | 同网段手机调试 |
| Android 模拟器 | `npx expo start --android` | 无手机时 |

## 11. 依赖清单

```json
{
  "expo": "~52.0.0",
  "expo-router": "~4.0.0",
  "expo-secure-store": "~14.0.0",
  "expo-image-picker": "~16.0.0",
  "expo-haptics": "~14.0.0",
  "react-native-reanimated": "~3.16.0",
  "react-native-gesture-handler": "~2.20.0",
  "zustand": "^5.0.0",
  "@react-native-async-storage/async-storage": "2.1.0"
}
```
