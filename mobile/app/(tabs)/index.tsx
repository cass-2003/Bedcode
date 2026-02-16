import { useEffect, useRef, useCallback, useState, useMemo } from 'react';
import { View, FlatList, StyleSheet, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useChatStore } from '../../stores/chatStore';
import { Colors } from '../../constants/theme';
import { useApi } from '../../hooks/useApi';
import StatusHeader from '../../components/StatusHeader';
import ChatBubble from '../../components/ChatBubble';
import ChatInput from '../../components/ChatInput';
import ThinkingIndicator from '../../components/ThinkingIndicator';
import CommandBar from '../../components/CommandBar';
import ActionBar from '../../components/ActionBar';
import TemplatePanel from '../../components/TemplatePanel';
import BatchPanel from '../../components/BatchPanel';
import HistoryPanel from '../../components/HistoryPanel';
import { addScheduledTask, getScheduledTasks, clearScheduledTasks } from '../../hooks/useScheduler';

const EMPTY_MSGS: any[] = [];

const completionMsg = () => ({
  id: `done-${Date.now()}`, type: 'system' as const, text: '✅ Claude 已完成', timestamp: Date.now(),
  actions: [
    { label: '🔄 重试', action: 'retry_again' },
    { label: '🔀 换方案', action: 'retry_alt' },
    { label: '✅ 已完成', action: 'done' },
    { label: '🔘 需要选择', action: 'waiting' },
  ],
});

const hasRecentCompletion = (msgs: any[]) =>
  msgs.slice(-5).some(m => m.type === 'system' && m.text?.includes('已完成') && Date.now() - m.timestamp < 10000);

export default function ChatScreen() {
  const claudeState = useChatStore(s => s.claudeState);
  const theme = useChatStore(s => s.theme);
  const currentMessages = useChatStore(s => s.currentHandle ? (s.messagesByHandle[s.currentHandle] || EMPTY_MSGS) : EMPTY_MSGS);
  const api = useApi();
  const router = useRouter();
  const c = Colors[theme];
  const [actionsVisible, setActionsVisible] = useState(false);
  const [tplVisible, setTplVisible] = useState(false);
  const [batchVisible, setBatchVisible] = useState(false);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const reversed = useMemo(() => [...currentMessages].reverse(), [currentMessages]);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const poll = async () => {
      const store = useChatStore.getState();

      // Fetch windows for multi-window state tracking
      const wRes = await api.getWindows().catch(() => null);
      const winList = wRes?.ok ? (wRes.data?.windows ?? wRes.data) : null;

      if (Array.isArray(winList)) {
        store.setWindows(winList);
        const prevStates = store.windowStates;
        const newStates: Record<number, string> = {};

        // Auto-select first/current window if no handle set
        if (!store.currentHandle) {
          const cur = winList.find((w: any) => w.current) || winList[0];
          if (cur) store.setCurrentHandle(cur.handle);
        }

        // Check each window for thinking→idle transitions
        for (const w of winList) {
          newStates[w.handle] = w.state;
          if (prevStates[w.handle] === 'thinking' && w.state !== 'thinking') {
            const bucket = store.messagesByHandle[w.handle] || [];
            if (!hasRecentCompletion(bucket)) {
              store.addMessageToHandle(w.handle, completionMsg());
            }
          }
        }
        store.setWindowStates(newStates);

        // Update current window info
        const curWin = winList.find((w: any) => w.handle === store.currentHandle) || winList.find((w: any) => w.current);
        if (curWin) {
          const newState = curWin.state === 'thinking' ? 'thinking' : 'idle';
          store.setClaudeState(newState);
          store.setWindowInfo(curWin.title || '', curWin.label || '');
        }
      }

      // Secondary status call for config sync (auto_monitor, screenshot_interval)
      const sRes = await api.getStatus().catch(() => null);
      if (sRes?.ok && sRes.data) {
        if (sRes.data.auto_monitor !== undefined) useChatStore.getState().setAutoMonitor(!!sRes.data.auto_monitor);
        if (sRes.data.screenshot_interval) useChatStore.getState().setScreenshotInterval(sRes.data.screenshot_interval);
      }
    };
    poll();
    pollRef.current = setInterval(poll, 5000);
    return () => clearInterval(pollRef.current);
  }, []);

  const handleSend = useCallback(async (text: string, imageUri?: string) => {
    const id = Date.now().toString();
    useChatStore.getState().addMessage({ id, type: 'sent', text, timestamp: Date.now(), status: 'sending', imageUri });
    const res = imageUri
      ? await api.sendImage(imageUri, text)
      : await api.sendMessage(text);
    const st = !res.ok ? 'failed' : res.data?.status === 'queued' ? 'queued' : res.data?.status === 'error' ? 'failed' : 'sent';
    useChatStore.getState().updateMessageStatus(id, st);
  }, []);

  const handleAction = useCallback(async (action: string) => {
    setActionsVisible(false);
    switch (action) {
      case 'screenshot': {
        const res = await api.getScreenshot();
        if (res.ok) useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: res.data });
        break;
      }
      case 'interrupt': {
        const res = await api.sendBreak();
        if (!res.ok) Alert.alert('错误', res.error || '中断失败');
        break;
      }
      case 'undo': {
        const res = await api.sendUndo();
        if (!res.ok) Alert.alert('错误', res.error || '撤销失败');
        break;
      }
      case 'grab': {
        const res = await api.getGrab();
        if (res.ok) useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'recv', text: res.data?.text || '', timestamp: Date.now() });
        break;
      }
      case 'window': router.navigate('/(tabs)/windows'); break;
      case 'cost': {
        const res = await api.getCost();
        if (res.ok) {
          const d = res.data;
          Alert.alert('💰 费用', `模型: ${d.model || '?'}\n轮次: ${d.turns || 0}\n输入: ${d.input_tokens?.toLocaleString() || 0}\n输出: ${d.output_tokens?.toLocaleString() || 0}\n总计: $${d.cost ?? 0}`);
        }
        break;
      }
      case 'export': {
        const res = await api.getExport();
        if (res.ok && res.data?.text) {
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'recv', text: res.data.text, timestamp: Date.now() });
        } else {
          Alert.alert('导出', '无内容');
        }
        break;
      }
      case 'clipboard': {
        const res = await api.getClipboard();
        if (res.ok) Alert.alert('剪贴板', res.data?.text || '(空)');
        break;
      }
      case 'toggle_monitor': {
        const current = useChatStore.getState().autoMonitor;
        const next = !current;
        await api.updateConfig({ auto_monitor: next });
        useChatStore.getState().setAutoMonitor(next);
        useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: next ? '👀 监控已开启' : '⏹ 监控已关闭', timestamp: Date.now() });
        break;
      }
      case 'templates': setTplVisible(true); break;
    }
  }, []);

  const handleShell = useCallback(async (cmd: string) => {
    useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'sent', text: `!${cmd}`, timestamp: Date.now(), status: 'sending' });
    const res = await api.runShell(cmd);
    if (res.ok) {
      useChatStore.getState().addMessage({ id: (Date.now() + 1).toString(), type: 'recv', text: res.data?.output || '(no output)', timestamp: Date.now() });
    }
  }, []);

  const handleKeys = useCallback(async (keys: string[]) => {
    await api.sendKeys(keys);
  }, []);

  const handleCommand = useCallback(async (cmd: string, args: string) => {
    // Check aliases first
    const aliases = useChatStore.getState().aliases;
    const resolved = aliases[cmd] || cmd;

    const map: Record<string, () => void> = {
      screenshot: () => handleAction('screenshot'),
      watch: () => handleAction('toggle_monitor'),
      monitor: () => handleAction('toggle_monitor'),
      stop: () => handleAction('interrupt'),
      break: () => api.sendBreak(),
      key: () => args && api.sendKeys(args.split(/\s+/)),
      cost: () => handleAction('cost'),
      grab: () => handleAction('grab'),
      undo: () => handleAction('undo'),
      export: () => handleAction('export'),
      clipboard: () => handleAction('clipboard'),
      clip: () => {
        if (args.startsWith('set ')) {
          const text = args.slice(4).trim();
          api.setClipboard(text).then(() => useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: '📋 已写入剪贴板', timestamp: Date.now() }));
        } else { handleAction('clipboard'); }
      },
      windows: () => router.navigate('/(tabs)/windows'),
      tpl: () => {
        const store = useChatStore.getState();
        if (!args) { setTplVisible(true); return; }
        const parts = args.split(' ');
        if (parts[0] === 'add' && parts.length >= 3) {
          store.setTemplates({ ...store.templates, [parts[1]]: parts.slice(2).join(' ') });
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `📝 模板 "${parts[1]}" 已保存`, timestamp: Date.now() });
        } else if (parts[0] === 'del' && parts[1]) {
          const next = { ...store.templates }; delete next[parts[1]]; store.setTemplates(next);
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🗑 模板 "${parts[1]}" 已删除`, timestamp: Date.now() });
        } else if (store.templates[args]) {
          handleSend(store.templates[args]);
        } else { setTplVisible(true); }
      },
      alias: () => {
        const store = useChatStore.getState();
        if (!args) {
          const list = Object.entries(store.aliases).map(([k, v]) => `/${k} → /${v}`).join('\n') || '(无别名)';
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🔗 别名列表:\n${list}`, timestamp: Date.now() });
        } else {
          const parts = args.split(' ');
          if (parts[0] === 'del' && parts[1]) {
            const next = { ...store.aliases }; delete next[parts[1]]; store.setAliases(next);
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🗑 别名 "${parts[1]}" 已删除`, timestamp: Date.now() });
          } else if (parts.length >= 2) {
            store.setAliases({ ...store.aliases, [parts[0]]: parts.slice(1).join(' ') });
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🔗 别名 /${parts[0]} → /${parts.slice(1).join(' ')}`, timestamp: Date.now() });
          }
        }
      },
      batch: () => {
        if (!args) { setBatchVisible(true); return; }
        const msgs = args.split('|').map(s => s.trim()).filter(Boolean);
        if (msgs.length) api.sendBatch(msgs).then(() => useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `📦 已批量发送 ${msgs.length} 条`, timestamp: Date.now() }));
      },
      queue: () => setBatchVisible(true),
      search: () => { setHistorySearch(args); setHistoryVisible(true); },
      history: () => { setHistorySearch(''); setHistoryVisible(true); },
      schedule: () => {
        if (!args) {
          const tasks = getScheduledTasks();
          const list = tasks.map(t => `• ${t.text} (${new Date(t.executeAt).toLocaleTimeString()})`).join('\n') || '(无定时任务)';
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `⏰ 定时任务:\n${list}`, timestamp: Date.now() });
        } else if (args === 'clear') {
          clearScheduledTasks();
          useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: '⏰ 已清除所有定时任务', timestamp: Date.now() });
        } else {
          const match = args.match(/^(\d+)(s|m|h)\s+(.+)$/);
          if (match) {
            const mult: Record<string, number> = { s: 1000, m: 60000, h: 3600000 };
            addScheduledTask(match[3], parseInt(match[1]) * mult[match[2]]);
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `⏰ 已计划: ${match[3]} (在 ${match[1]}${match[2]} 后)`, timestamp: Date.now() });
          } else { handleSend(`/schedule ${args}`); }
        }
      },
      panel: () => {
        const store = useChatStore.getState();
        if (!args || args === 'reset') {
          store.setCustomButtons([]);
          if (args === 'reset') useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: '🎛 面板已重置', timestamp: Date.now() });
          else {
            const list = (store.customButtons.length ? store.customButtons : []).map(b => `${b.icon} ${b.label} → ${b.action}`).join('\n') || '(使用默认面板)';
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🎛 自定义面板:\n${list}`, timestamp: Date.now() });
          }
        } else {
          const parts = args.split(' ');
          if (parts[0] === 'add' && parts.length >= 3) {
            const icon = parts[1], label = parts[2], action = parts[3] || parts[2].toLowerCase();
            store.setCustomButtons([...store.customButtons, { icon, label, action }]);
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🎛 已添加按钮: ${icon} ${label}`, timestamp: Date.now() });
          } else if (parts[0] === 'del' && parts[1]) {
            store.setCustomButtons(store.customButtons.filter(b => b.label !== parts[1]));
            useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'system', text: `🗑 已删除按钮: ${parts[1]}`, timestamp: Date.now() });
          }
        }
      },
    };
    const handler = map[resolved];
    if (handler) {
      handler();
    } else {
      handleSend(`/${resolved}${args ? ' ' + args : ''}`);
    }
  }, [handleAction, handleSend]);

  const handleBubbleAction = useCallback(async (action: string, keys?: string) => {
    const api2 = api;
    switch (action) {
      case 'retry_again':
        await api2.sendMessage('请重试上一个操作');
        break;
      case 'retry_alt':
        await api2.sendMessage('请换一种方案重新实现');
        break;
      case 'done':
        break;
      case 'waiting':
        const res = await api2.getScreenshot();
        if (res.ok) useChatStore.getState().addMessage({ id: Date.now().toString(), type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: res.data });
        break;
      default:
        if (keys) await api2.sendKeys(keys.split(' '));
        break;
    }
  }, []);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: c.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={0}
    >
      <StatusHeader onAction={() => setActionsVisible(true)} />
      <FlatList
        data={reversed}
        keyExtractor={(m) => m.id}
        renderItem={({ item }) => <ChatBubble {...item} onAction={handleBubbleAction} />}
        inverted
        contentContainerStyle={styles.list}
        keyboardDismissMode="interactive"
      />
      {claudeState === 'thinking' && <ThinkingIndicator />}
      <ActionBar onAction={handleAction} />
      <ChatInput onSend={handleSend} onCommand={handleCommand} />
      <CommandBar visible={actionsVisible} onClose={() => setActionsVisible(false)} onAction={handleAction} onShell={handleShell} onKeys={handleKeys} />
      <TemplatePanel visible={tplVisible} onClose={() => setTplVisible(false)} onSend={handleSend} />
      <BatchPanel visible={batchVisible} onClose={() => setBatchVisible(false)} />
      <HistoryPanel visible={historyVisible} onClose={() => setHistoryVisible(false)} onSend={handleSend} initialSearch={historySearch} />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { paddingHorizontal: 12, paddingVertical: 8, paddingBottom: 100 },
});
