import { useEffect, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';

export function useAutoMonitor() {
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const check = () => {
      const { claudeState, autoMonitor, connected } = useChatStore.getState();
      const shouldRun = claudeState === 'thinking' && autoMonitor && connected;

      if (shouldRun && !intervalRef.current) {
        const ms = (useChatStore.getState().screenshotInterval || 15) * 1000;
        intervalRef.current = setInterval(async () => {
          const s = useChatStore.getState();
          if (s.claudeState !== 'thinking' || !s.autoMonitor || !s.host || !s.token) {
            clearInterval(intervalRef.current);
            intervalRef.current = undefined;
            return;
          }
          try {
            const res = await fetch(`${s.host}/api/screenshot`, {
              headers: { Authorization: `Bearer ${s.token}` },
            });
            if (!res.ok) return;
            const blob = await res.blob();
            const base64: string = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
              reader.onerror = reject;
              reader.readAsDataURL(blob);
            });
            const handle = useChatStore.getState().currentHandle;
            if (!handle) return;
            useChatStore.getState().addMessageToHandle(handle, {
              id: `auto-${Date.now()}`,
              type: 'screenshot',
              text: '',
              timestamp: Date.now(),
              imageBase64: base64,
            });
          } catch {}
        }, ms);
      } else if (!shouldRun && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = undefined;
      }
    };

    const unsub = useChatStore.subscribe(check);
    check();
    return () => {
      unsub();
      clearInterval(intervalRef.current);
    };
  }, []);
}
