import { useChatStore } from '../stores/chatStore';

type ApiResult = { ok: boolean; data?: any; error?: string };

function getAuth() {
  const { host, token } = useChatStore.getState();
  return { host, token };
}

async function _fetch(path: string, options?: RequestInit): Promise<ApiResult> {
  const { host, token } = getAuth();
  if (!host || !token) return { ok: false, error: 'Not connected' };
  try {
    const res = await fetch(`${host}${path}`, {
      ...options,
      headers: {
        ...(options?.headers || {}),
        ...(!isFormData(options?.body) ? { 'Content-Type': 'application/json' } : {}),
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = await res.json().catch(() => null);
    return { ok: true, data };
  } catch (e: any) {
    return { ok: false, error: e.message || 'Network error' };
  }
}

function isFormData(body: any): body is FormData {
  return body instanceof FormData;
}

export function useApi() {
  return {
    getStatus: () => _fetch('/api/status'),
    getScreenshot: async (): Promise<ApiResult> => {
      const { host, token } = getAuth();
      if (!host || !token) return { ok: false, error: 'Not connected' };
      try {
        const res = await fetch(`${host}/api/screenshot`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
        const blob = await res.blob();
        const base64: string = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        return { ok: true, data: base64 };
      } catch (e: any) {
        return { ok: false, error: e.message || 'Network error' };
      }
    },
    sendMessage: (text: string) => _fetch('/api/send', { method: 'POST', body: JSON.stringify({ text }) }),
    sendImage: (uri: string, caption: string) => {
      const form = new FormData();
      form.append('file', { uri, name: 'image.jpg', type: 'image/jpeg' } as any);
      form.append('caption', caption);
      return _fetch('/api/image', { method: 'POST', body: form });
    },
    sendBreak: () => _fetch('/api/break', { method: 'POST' }),
    sendUndo: () => _fetch('/api/undo', { method: 'POST' }),
    sendKeys: (keys: string[]) => _fetch('/api/keys', { method: 'POST', body: JSON.stringify({ keys }) }),
    getGrab: () => _fetch('/api/grab'),
    getWindows: () => _fetch('/api/windows'),
    setTarget: (handle: number) => _fetch('/api/target', { method: 'POST', body: JSON.stringify({ handle }) }),
    getCost: () => _fetch('/api/cost'),
    getHistory: () => _fetch('/api/history'),
    getQueue: () => _fetch('/api/queue'),
    clearQueue: () => _fetch('/api/queue', { method: 'DELETE' }),
    getExport: () => _fetch('/api/export'),
    getClipboard: () => _fetch('/api/clipboard'),
    setClipboard: (text: string) => _fetch('/api/clipboard', { method: 'POST', body: JSON.stringify({ text }) }),
    updateConfig: (config: Record<string, any>) => _fetch('/api/config', { method: 'PATCH', body: JSON.stringify(config) }),
    runShell: (cmd: string) => _fetch('/api/shell', { method: 'POST', body: JSON.stringify({ cmd }) }),
    sendBatch: (messages: string[]) => _fetch('/api/batch', { method: 'POST', body: JSON.stringify({ messages }) }),
    setLabel: (handle: number, label: string) => _fetch('/api/label', { method: 'POST', body: JSON.stringify({ handle, label }) }),
  };
}
