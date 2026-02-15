import { useEffect, useRef, useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';

export function useWebSocket() {
  const host = useChatStore((s) => s.host);
  const token = useChatStore((s) => s.token);
  const connected = useChatStore((s) => s.connected);
  const addMessage = useChatStore((s) => s.addMessage);
  const setClaudeState = useChatStore((s) => s.setClaudeState);
  const setConnected = useChatStore((s) => s.setConnected);
  const setWindowInfo = useChatStore((s) => s.setWindowInfo);

  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const pingRef = useRef<ReturnType<typeof setInterval>>();
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const cleanup = useCallback(() => {
    if (pingRef.current) clearInterval(pingRef.current);
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!host || !token || !mountedRef.current) return;
    cleanup();

    const wsUrl = host.replace(/^http/, 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ token }));
      backoffRef.current = 1000;
      setConnected(true);
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 25000);
    };

    ws.onmessage = (e) => {
      let msg: any;
      try { msg = JSON.parse(e.data); } catch { return; }
      const id = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      switch (msg.type) {
        case 'screenshot':
          addMessage({ id: id(), type: 'screenshot', text: '', timestamp: Date.now(), imageBase64: msg.data });
          break;
        case 'status':
          if (msg.state) setClaudeState(msg.state);
          if (msg.title !== undefined) setWindowInfo(msg.title || '', msg.label || '');
          break;
        case 'result':
          addMessage({ id: id(), type: 'recv', text: msg.text || msg.data || '', timestamp: Date.now() });
          break;
        case 'completion':
          addMessage({ id: id(), type: 'system', text: msg.text || msg.data || 'Claude 已完成', timestamp: Date.now(), actions: msg.actions || [] });
          break;
        case 'prompt':
          addMessage({
            id: id(),
            type: 'prompt',
            text: msg.text || '',
            timestamp: Date.now(),
            actions: msg.options?.map((o: any) => ({ label: o.label, keys: o.keys })) || [],
          });
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingRef.current) clearInterval(pingRef.current);
      if (!mountedRef.current) return;
      const delay = Math.min(backoffRef.current, 30000);
      backoffRef.current = delay * 2;
      reconnectRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [host, token, cleanup, addMessage, setClaudeState, setConnected, setWindowInfo]);

  useEffect(() => {
    mountedRef.current = true;
    if (host && token) connect();
    return () => {
      mountedRef.current = false;
      cleanup();
      setConnected(false);
    };
  }, [host, token, connect, cleanup, setConnected]);

  return { connected, reconnect: connect };
}
