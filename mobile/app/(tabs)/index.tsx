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

export default function ChatScreen() {
  const { messages, claudeState, theme, addMessage, updateMessageStatus, setClaudeState, setWindowInfo } = useChatStore();
  const api = useApi();
  const router = useRouter();
  const c = Colors[theme];
  const [actionsVisible, setActionsVisible] = useState(false);
  const reversed = useMemo(() => [...messages].reverse(), [messages]);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const poll = async () => {
      const res = await api.getStatus().catch(() => null);
      if (res?.ok && res.data) {
        if (res.data.state) setClaudeState(res.data.state === 'thinking' ? 'thinking' : 'idle');
        setWindowInfo(res.data.title || '', res.data.label || '');
      }
    };
    poll();
    pollRef.current = setInterval(poll, 5000);
    return () => clearInterval(pollRef.current);
  }, []);

  const handleSend = useCallback(async (text: string, imageUri?: string) => {
    const id = Date.now().toString();
    addMessage({ id, type: 'sent', text, timestamp: Date.now(), status: 'sending', imageUri });
    const res = imageUri
      ? await api.sendImage(imageUri, text)
      : await api.sendMessage(text);
    const st = !res.ok ? 'failed' : res.data?.status === 'queued' ? 'queued' : res.data?.status === 'error' ? 'failed' : 'sent';
    updateMessageStatus(id, st);
  }, []);

  const handleAction = useCallback(async (action: string) => {
    setActionsVisible(false);
    switch (action) {
      case 'screenshot': {
        const res = await api.getScreenshot();
        if (res.ok) addMessage({ id: Date.now().toString(), type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: res.data });
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
        if (res.ok) addMessage({ id: Date.now().toString(), type: 'recv', text: res.data?.text || '', timestamp: Date.now() });
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
          addMessage({ id: Date.now().toString(), type: 'recv', text: res.data.text, timestamp: Date.now() });
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
    }
  }, []);

  const handleShell = useCallback(async (cmd: string) => {
    addMessage({ id: Date.now().toString(), type: 'sent', text: `!${cmd}`, timestamp: Date.now(), status: 'sending' });
    const res = await api.runShell(cmd);
    if (res.ok) {
      addMessage({ id: (Date.now() + 1).toString(), type: 'recv', text: res.data?.output || '(no output)', timestamp: Date.now() });
    }
  }, []);

  const handleKeys = useCallback(async (keys: string[]) => {
    await api.sendKeys(keys);
  }, []);

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
        if (res.ok) addMessage({ id: Date.now().toString(), type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: res.data });
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
      <ChatInput onSend={handleSend} />
      <CommandBar visible={actionsVisible} onClose={() => setActionsVisible(false)} onAction={handleAction} onShell={handleShell} onKeys={handleKeys} />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { paddingHorizontal: 12, paddingVertical: 8 },
  bottomSpacer: { height: 56 },
});
