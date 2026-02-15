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
  messages: Message[];
  windows: WindowInfo[];
  theme: 'dark' | 'light';

  setAuth: (host: string, token: string) => void;
  clearAuth: () => void;
  addMessage: (msg: Message) => void;
  updateMessageStatus: (id: string, status: Message['status']) => void;
  setClaudeState: (state: ChatState['claudeState']) => void;
  setWindows: (wins: WindowInfo[]) => void;
  setConnected: (connected: boolean) => void;
  setTheme: (theme: ChatState['theme']) => void;
  setWindowInfo: (title: string, label: string) => void;
}

const MAX_MESSAGES = 80;

const persistMessages = (messages: Message[]) => {
  AsyncStorage.setItem('messages', JSON.stringify(messages.slice(-MAX_MESSAGES))).catch(() => {});
};

export const useChatStore = create<ChatState>((set, get) => {
  // Load persisted values on creation
  (async () => {
    try {
      const [host, token, messagesRaw, theme] = await Promise.all([
        SecureStore.getItemAsync('host'),
        SecureStore.getItemAsync('token'),
        AsyncStorage.getItem('messages'),
        AsyncStorage.getItem('theme'),
      ]);
      set({
        ...(host && token ? { host, token } : {}),
        ...(messagesRaw ? { messages: JSON.parse(messagesRaw) } : {}),
        ...(theme === 'dark' || theme === 'light' ? { theme } : {}),
      });
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
    messages: [],
    windows: [],
    theme: 'dark',

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
      const messages = [...get().messages, msg].slice(-MAX_MESSAGES);
      persistMessages(messages);
      set({ messages });
    },

    updateMessageStatus: (id, status) => {
      const messages = get().messages.map((m) => (m.id === id ? { ...m, status } : m));
      persistMessages(messages);
      set({ messages });
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
  };
});
