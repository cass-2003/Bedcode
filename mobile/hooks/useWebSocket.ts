import { useEffect, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const pingRef = useRef<ReturnType<typeof setInterval>>();
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    const tryConnect = () => {
      const { host, token } = useChatStore.getState();
      if (!host || !token || !mountedRef.current) return;

      // cleanup previous
      if (pingRef.current) clearInterval(pingRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }

      const wsUrl = host.replace(/^http/, 'ws') + '/ws';
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ token }));
        backoffRef.current = 1000;
        useChatStore.getState().setConnected(true);
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 15000);
      };

      ws.onmessage = (e) => {
        let msg: any;
        try { msg = JSON.parse(e.data); } catch { return; }
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const store = useChatStore.getState();

        switch (msg.type) {
          case 'screenshot':
            store.addMessage({ id, type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: msg.data });
            break;
          case 'status':
            if (msg.state) store.setClaudeState(msg.state);
            if (msg.title !== undefined) store.setWindowInfo(msg.title || '', msg.label || '');
            break;
          case 'result':
            store.addMessage({ id, type: 'recv', text: msg.text || msg.data || '', timestamp: Date.now() });
            break;
          case 'completion':
            store.addMessage({ id, type: 'system', text: msg.text || msg.data || 'Claude 已完成', timestamp: Date.now(), actions: msg.actions || [] });
            break;
          case 'prompt':
            store.addMessage({
              id, type: 'prompt', text: msg.text || '', timestamp: Date.now(),
              actions: msg.options?.map((o: any) => ({ label: o.label, keys: o.keys })) || [],
            });
            break;
        }
      };

      ws.onclose = () => {
        useChatStore.getState().setConnected(false);
        if (pingRef.current) clearInterval(pingRef.current);
        if (!mountedRef.current) return;
        const delay = Math.min(backoffRef.current, 30000);
        backoffRef.current = delay * 2;
        reconnectRef.current = setTimeout(tryConnect, delay);
      };

      ws.onerror = () => ws.close();
    };

    // Subscribe to host/token changes — connect when they become available
    const unsub = useChatStore.subscribe((state, prev) => {
      if (state.host && state.token && (state.host !== prev.host || state.token !== prev.token)) {
        backoffRef.current = 1000;
        tryConnect();
      }
    });

    // Initial connect attempt
    tryConnect();

    return () => {
      mountedRef.current = false;
      unsub();
      if (pingRef.current) clearInterval(pingRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      useChatStore.getState().setConnected(false);
    };
  }, []);
}
