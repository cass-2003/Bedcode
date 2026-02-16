# Multi-Window Chat Refactor

## 概述
将 app 从单一全局消息列表改造为多窗口独立聊天模式，类似 Telegram/微信的多聊天体验。每个 Claude Code 窗口拥有独立的消息历史、未读计数和状态追踪。

## 改动文件

### 1. `stores/chatStore.ts` — 核心数据层重构
- `messages: Message[]` → `messagesByHandle: Record<number, Message[]>` 按窗口 handle 分桶存储
- 新增 `currentHandle: number | null` 当前活跃窗口
- 新增 `windowStates: Record<number, string>` 所有窗口状态追踪（用于检测 thinking→idle）
- 新增 `unreadByHandle: Record<number, number>` 每窗口未读计数
- 新增方法：
  - `addMessageToHandle(handle, msg)` — 写入指定窗口消息桶，非当前窗口自动 +1 未读
  - `setCurrentHandle(handle)` — 切换窗口，懒加载持久化消息，清除未读
  - `clearUnread(handle)` — 清除指定窗口未读
  - `setWindowStates(states)` — 更新全窗口状态
  - `incrementUnread(handle)` — 手动增加未读
- 持久化从 `AsyncStorage('messages')` → `AsyncStorage('messages_${handle}')` 按窗口分 key
- 旧数据迁移：首次启动时将全局 `messages` 迁移到第一个窗口

### 2. `app/(tabs)/windows.tsx` — 聊天列表 UI
- 从简单窗口列表改为 Telegram 风格聊天列表
- 每行显示：头像（标签首字母）、状态圆点（thinking=黄/idle=绿）、名称、最后消息预览、时间、未读红点
- 点击 → `setTarget` + `setCurrentHandle` + 跳转聊天页
- 长按 → 编辑标签（保留原有功能）
- 时间格式：今天显示 HH:MM，本周显示星期，更早显示 M/D

### 3. `app/(tabs)/index.tsx` — 多窗口轮询
- 轮询从 `GET /api/status` 改为 `GET /api/windows`，一次获取所有窗口状态
- 对比 `windowStates` 检测任意窗口 thinking→idle 变化
- 当前窗口变化 → 正常写消息
- 非当前窗口变化 → `addMessageToHandle` 写入对应桶 + 自动增加未读
- 自动选择：首次无 currentHandle 时自动选中第一个/当前窗口
- 消息显示从 `messages` 改为 `messagesByHandle[currentHandle]`
- 保留 `/api/status` 二次调用用于同步 auto_monitor/screenshot_interval 配置

### 4. `hooks/useAutoMonitor.ts` — 截屏存入正确窗口
- `addMessage` → `addMessageToHandle(currentHandle, ...)` 确保自动截屏存入当前窗口桶

## 后端改动
无。所有改动仅在前端。

## 数据流

```
每 5 秒轮询 GET /api/windows
  → [{handle, title, state, label}, ...]
  → 对比 windowStates
  → 窗口 X: thinking → idle?
     → 当前 handle: 写完成消息到当前桶
     → 非当前 handle: 写完成消息到 X 桶 + unread[X]++
  → 更新 windowStates
  → windows.tsx 显示未读红点
```

## 迁移说明
- 旧版全局 `messages` AsyncStorage key 会在首次启动时自动迁移到第一个窗口
- 迁移后旧 key 被删除
- 无需手动操作
