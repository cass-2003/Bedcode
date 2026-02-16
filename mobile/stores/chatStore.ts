import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

export interface Message {
  id: string;
  type: 'sent' | 'recv' | 'system' | 'screenshot' | 'prompt';
  text: string;
  timestamp: number;
  status?: 'sending' | 'sent' | 'injected' | 'queued' | 'failed';
  imageBase64?: string;
  imageUri?: string;
  actions?: Array<{label: string; action?: string; keys?: string}>;
}

export interface WindowInfo {
  handle: number;
  title: string;
  state: string;
  label: string;
  current: boolean;
}

interface ChatState {
  host: string;
  token: string;
  connected: boolean;
  claudeState: 'thinking' | 'idle' | 'unknown';
  windowTitle: string;
  windowLabel: string;
  thinkingStart: number | null;
  currentHandle: number | null;
  messagesByHandle: Record<number, Message[]>;
  windowStates: Record<number, string>;
  unreadByHandle: Record<number, number>;
  windows: WindowInfo[];
  theme: 'dark' | 'light';
  autoMonitor: boolean;
  screenshotInterval: number;
  templates: Record<string, string>;
  aliases: Record<string, string>;
  customButtons: Array<{icon: string; label: string; action: string}>;

  setAuth: (host: string, token: string) => void;
  clearAuth: () => void;
  addMessage: (msg: Message) => void;
  addMessageToHandle: (handle: number, msg: Message) => void;
  updateMessageStatus: (id: string, status: Message['status']) => void;
  setClaudeState: (state: ChatState['claudeState']) => void;
  setWindows: (wins: WindowInfo[]) => void;
  setConnected: (connected: boolean) => void;
  setTheme: (theme: ChatState['theme']) => void;
  setWindowInfo: (title: string, label: string) => void;
  setAutoMonitor: (enabled: boolean) => void;
  setScreenshotInterval: (seconds: number) => void;
  setTemplates: (templates: Record<string, string>) => void;
  setAliases: (aliases: Record<string, string>) => void;
  setCustomButtons: (buttons: Array<{icon: string; label: string; action: string}>) => void;
  setCurrentHandle: (handle: number | null) => void;
  clearUnread: (handle: number) => void;
  setWindowStates: (states: Record<number, string>) => void;
  incrementUnread: (handle: number) => void;
}

const MAX_MESSAGES = 80;

const persistHandleMessages = (handle: number, messages: Message[]) => {
  AsyncStorage.setItem(`messages_${handle}`, JSON.stringify(messages.slice(-MAX_MESSAGES))).catch(() => {});
};

const loadHandleMessages = async (handle: number): Promise<Message[]> => {
  try {
    const raw = await AsyncStorage.getItem(`messages_${handle}`);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
};

export const useChatStore = create<ChatState>((set, get) => {
  // Load persisted values on creation
  (async () => {
    try {
      const [host, token, theme, templatesRaw, aliasesRaw, customButtonsRaw] = await Promise.all([
        SecureStore.getItemAsync('host'),
        SecureStore.getItemAsync('token'),
        AsyncStorage.getItem('theme'),
        AsyncStorage.getItem('templates'),
        AsyncStorage.getItem('aliases'),
        AsyncStorage.getItem('customButtons'),
      ]);
      set({
        ...(host && token ? { host, token } : {}),
        ...(theme === 'dark' || theme === 'light' ? { theme } : {}),
        ...(templatesRaw ? { templates: JSON.parse(templatesRaw) } : {}),
        ...(aliasesRaw ? { aliases: JSON.parse(aliasesRaw) } : {}),
        ...(customButtonsRaw ? { customButtons: JSON.parse(customButtonsRaw) } : {}),
      });
      // Migrate old global messages to first window if exists
      const oldMessages = await AsyncStorage.getItem('messages');
      if (oldMessages) {
        const msgs: Message[] = JSON.parse(oldMessages);
        if (msgs.length > 0) {
          // Will be assigned to first window on first setCurrentHandle
          set({ _migrationMessages: msgs } as any);
        }
        AsyncStorage.removeItem('messages').catch(() => {});
      }
    } catch {}
  })();

  return {
    host: '',
    token: '',
    connected: false,
    claudeState: 'unknown',
    windowTitle: '',
    windowLabel: '',
    thinkingStart: null,
    currentHandle: null,
    messagesByHandle: {},
    windowStates: {},
    unreadByHandle: {},
    windows: [],
    theme: 'dark',
    autoMonitor: false,
    screenshotInterval: 15,
    templates: {},
    aliases: {},
    customButtons: [],

    setAuth: (host, token) => {
      SecureStore.setItemAsync('host', host).catch(() => {});
      SecureStore.setItemAsync('token', token).catch(() => {});
      set({ host, token });
    },

    clearAuth: () => {
      SecureStore.deleteItemAsync('host').catch(() => {});
      SecureStore.deleteItemAsync('token').catch(() => {});
      set({ host: '', token: '', connected: false });
    },

    addMessage: (msg) => {
      const { currentHandle, messagesByHandle } = get();
      if (!currentHandle) return;
      const msgs = [...(messagesByHandle[currentHandle] || []), msg].slice(-MAX_MESSAGES);
      persistHandleMessages(currentHandle, msgs);
      set({ messagesByHandle: { ...messagesByHandle, [currentHandle]: msgs } });
    },

    addMessageToHandle: (handle, msg) => {
      const { messagesByHandle, currentHandle, unreadByHandle } = get();
      const msgs = [...(messagesByHandle[handle] || []), msg].slice(-MAX_MESSAGES);
      persistHandleMessages(handle, msgs);
      const updates: any = { messagesByHandle: { ...messagesByHandle, [handle]: msgs } };
      if (handle !== currentHandle) {
        updates.unreadByHandle = { ...unreadByHandle, [handle]: (unreadByHandle[handle] || 0) + 1 };
      }
      set(updates);
    },

    updateMessageStatus: (id, status) => {
      const { currentHandle, messagesByHandle } = get();
      if (!currentHandle) return;
      const msgs = (messagesByHandle[currentHandle] || []).map((m) => (m.id === id ? { ...m, status } : m));
      persistHandleMessages(currentHandle, msgs);
      set({ messagesByHandle: { ...messagesByHandle, [currentHandle]: msgs } });
    },

    setClaudeState: (claudeState) => {
      const prev = get().claudeState;
      if (prev === claudeState) return;
      set({
        claudeState,
        thinkingStart: claudeState === 'thinking' ? Date.now() : null,
      });
    },

    setWindows: (windows) => set({ windows }),
    setConnected: (connected) => set({ connected }),

    setTheme: (theme) => {
      AsyncStorage.setItem('theme', theme).catch(() => {});
      set({ theme });
    },

    setWindowInfo: (windowTitle, windowLabel) => set({ windowTitle, windowLabel }),
    setAutoMonitor: (autoMonitor) => set({ autoMonitor }),
    setScreenshotInterval: (screenshotInterval) => set({ screenshotInterval }),

    setTemplates: (templates) => {
      AsyncStorage.setItem('templates', JSON.stringify(templates)).catch(() => {});
      set({ templates });
    },
    setAliases: (aliases) => {
      AsyncStorage.setItem('aliases', JSON.stringify(aliases)).catch(() => {});
      set({ aliases });
    },
    setCustomButtons: (customButtons) => {
      AsyncStorage.setItem('customButtons', JSON.stringify(customButtons)).catch(() => {});
      set({ customButtons });
    },

    setCurrentHandle: async (handle) => {
      if (!handle) { set({ currentHandle: null }); return; }
      const { messagesByHandle } = get();
      if (!messagesByHandle[handle]) {
        const msgs = await loadHandleMessages(handle);
        // Check for migration messages
        const migration = (get() as any)._migrationMessages;
        const finalMsgs = migration && msgs.length === 0 ? migration : msgs;
        set({
          currentHandle: handle,
          messagesByHandle: { ...get().messagesByHandle, [handle]: finalMsgs },
          unreadByHandle: { ...get().unreadByHandle, [handle]: 0 },
          _migrationMessages: undefined,
        } as any);
      } else {
        set({ currentHandle: handle, unreadByHandle: { ...get().unreadByHandle, [handle]: 0 } });
      }
    },

    clearUnread: (handle) => {
      set({ unreadByHandle: { ...get().unreadByHandle, [handle]: 0 } });
    },

    setWindowStates: (windowStates) => set({ windowStates }),

    incrementUnread: (handle) => {
      const { unreadByHandle } = get();
      set({ unreadByHandle: { ...unreadByHandle, [handle]: (unreadByHandle[handle] || 0) + 1 } });
    },
  };
});
